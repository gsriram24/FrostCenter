"""
EC (Embedded Controller) access via /dev/port using the ACPI EC protocol.

This replaces the ec_sys kernel module (debugfs) approach with direct
port I/O, which works on Bazzite and other immutable distros where
CONFIG_ACPI_EC_DEBUGFS is not compiled into the kernel.

Protocol reference: ACPI Specification 6.5, Chapter 12
Implementation reference: nbfc-linux ec_linux.c (dev_port backend)
"""

import os


# ACPI EC I/O ports
EC_SC = 0x66        # Status (read) / Command (write) port
EC_DATA = 0x62      # Data port

# EC commands
EC_CMD_READ = 0x80   # Read EC register
EC_CMD_WRITE = 0x81  # Write EC register

# Status register bits
EC_SC_IBF = 0x02     # Input Buffer Full
EC_SC_OBF = 0x01     # Output Buffer Full

# Timing
EC_POLL_TIMEOUT = 500  # Max polling iterations per wait
EC_MAX_RETRIES = 5     # Max retries per read/write operation


class ECTimeoutError(Exception):
    """Raised when an EC operation times out."""
    pass


class ECAccessError(Exception):
    """Raised when /dev/port cannot be opened."""
    pass


class ECAccess:
    """Low-level EC access via /dev/port using the ACPI EC protocol.

    The EC uses two I/O ports:
      - Port 0x66 (EC_SC): status register (read) / command register (write)
      - Port 0x62 (EC_DATA): data register (read/write)

    Read sequence:  wait IBF clear -> cmd 0x80 -> wait IBF clear ->
                    send register addr -> wait IBF clear -> wait OBF set ->
                    read data byte
    Write sequence: wait IBF clear -> cmd 0x81 -> wait IBF clear ->
                    send register addr -> wait IBF clear ->
                    send data byte -> wait IBF clear
    """

    def __init__(self, read_only=False):
        """Open /dev/port for EC access.

        Args:
            read_only: If True, write_byte() raises RuntimeError.
                       Use this for safe monitoring without fan control.
        """
        self._read_only = read_only
        self._fd = None
        try:
            self._fd = os.open('/dev/port', os.O_RDWR)
        except PermissionError:
            raise ECAccessError(
                "Cannot open /dev/port: permission denied. "
                "Run with sudo or as root."
            )
        except FileNotFoundError:
            raise ECAccessError(
                "Cannot open /dev/port: file not found. "
                "This may happen if Secure Boot is enabled (kernel lockdown)."
            )

    def close(self):
        """Close the /dev/port file descriptor."""
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def _read_port(self, port):
        """Read one byte from an I/O port."""
        return os.pread(self._fd, 1, port)[0]

    def _write_port(self, port, value):
        """Write one byte to an I/O port."""
        os.pwrite(self._fd, bytes([value]), port)

    def _wait_ibf_clear(self):
        """Wait for the EC Input Buffer Full flag to clear.

        The host must wait for IBF=0 before sending a new byte to the EC.
        """
        for _ in range(EC_POLL_TIMEOUT):
            if not (self._read_port(EC_SC) & EC_SC_IBF):
                return
        raise ECTimeoutError("EC input buffer did not clear (IBF timeout)")

    def _wait_obf_set(self):
        """Wait for the EC Output Buffer Full flag to set.

        The host must wait for OBF=1 before reading data from the EC.
        """
        for _ in range(EC_POLL_TIMEOUT):
            if self._read_port(EC_SC) & EC_SC_OBF:
                return
        raise ECTimeoutError("EC output buffer not ready (OBF timeout)")

    def _do_read(self, register):
        """Execute one EC read attempt (no retry)."""
        self._wait_ibf_clear()
        self._write_port(EC_SC, EC_CMD_READ)
        self._wait_ibf_clear()
        self._write_port(EC_DATA, register)
        self._wait_ibf_clear()
        self._wait_obf_set()
        return self._read_port(EC_DATA)

    def _do_write(self, register, value):
        """Execute one EC write attempt (no retry)."""
        self._wait_ibf_clear()
        self._write_port(EC_SC, EC_CMD_WRITE)
        self._wait_ibf_clear()
        self._write_port(EC_DATA, register)
        self._wait_ibf_clear()
        self._write_port(EC_DATA, value)
        self._wait_ibf_clear()

    def read_byte(self, register):
        """Read one byte from an EC register.

        Args:
            register: EC register address (0x00-0xFF)

        Returns:
            Integer value 0-255

        Raises:
            ECTimeoutError: If the EC does not respond after retries
        """
        last_error = None
        for attempt in range(EC_MAX_RETRIES):
            try:
                return self._do_read(register)
            except ECTimeoutError as e:
                last_error = e
        raise ECTimeoutError(
            f"EC read from register 0x{register:02x} failed after "
            f"{EC_MAX_RETRIES} retries: {last_error}"
        )

    def read_word(self, register):
        """Read two consecutive bytes as a big-endian 16-bit integer.

        Used for fan RPM registers where the value spans two bytes.
        Matches the original OFC.py behavior: int(file.read(2).hex(), 16)
        which reads [register] as MSB and [register+1] as LSB.

        Args:
            register: EC register address of the high byte

        Returns:
            Integer value 0-65535
        """
        high = self.read_byte(register)
        low = self.read_byte(register + 1)
        return (high << 8) | low

    def write_byte(self, register, value):
        """Write one byte to an EC register.

        Args:
            register: EC register address (0x00-0xFF)
            value: Value to write (0x00-0xFF)

        Raises:
            RuntimeError: If the instance was created with read_only=True
            ECTimeoutError: If the EC does not respond after retries
        """
        if self._read_only:
            raise RuntimeError(
                "Write operations disabled in read-only mode. "
                "Set read_only=False to enable EC writes."
            )

        last_error = None
        for attempt in range(EC_MAX_RETRIES):
            try:
                self._do_write(register, value)
                return
            except ECTimeoutError as e:
                last_error = e
        raise ECTimeoutError(
            f"EC write to register 0x{register:02x} failed after "
            f"{EC_MAX_RETRIES} retries: {last_error}"
        )

    @property
    def is_read_only(self):
        """Whether this instance is in read-only mode."""
        return self._read_only

    @is_read_only.setter
    def is_read_only(self, value):
        """Set read-only mode at runtime."""
        self._read_only = bool(value)


def get_lockdown_status():
    """Read kernel lockdown status. Returns one of 'none', 'integrity', 'confidentiality', or 'unknown'."""
    try:
        with open('/sys/kernel/security/lockdown', 'r') as f:
            text = f.read().strip()
            # Format is like: "none [integrity] confidentiality" with brackets on active
            for token in text.split():
                if token.startswith('[') and token.endswith(']'):
                    return token[1:-1]
            return 'unknown'
    except (FileNotFoundError, PermissionError):
        return 'unknown'
