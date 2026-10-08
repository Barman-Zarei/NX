# Risk and compatibility matrix
| Item | Risk | Status |
|---|---|---|
| 32-bit boot | No complete i386 Ubuntu base | Not supported |
| Secure Boot | grub-mkrescue image is unsigned | Not supported |
| Windows 7 host tools | Python 3.8 / Qt 5.15 EOL, no security updates | Planned, untested |
| Dual boot / BitLocker | Needs careful installer design | Planned |
| Wine/Proton | Cannot promise full compatibility | Planned |
| Build env | No /dev/kvm: VM tests run under slow TCG emulation | Known limitation |
