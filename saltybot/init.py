"""
Saltybot core package.
"""

from importlib.metadata import version, PackageNotFoundError

__all__ = ["__version__"]

try:
    __version__ = version("saltybot")
except PackageNotFoundError:
    # เมื่อยังไม่ได้ติดตั้งเป็นแพ็กเกจ (รันจากซอร์ส)
    __version__ = "0.0.0"
