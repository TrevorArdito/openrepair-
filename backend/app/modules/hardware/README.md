# Hardware module (DISABLED by default — not built yet)

Future home of OBD-II live data and code reading (ELM327, J2534 pass-thru), and later
key programming and ECU tuning.

Rules every hardware feature must follow:

1. **Off by default.** Only loaded when `ENABLE_HARDWARE=true`.
2. **Clear safety warnings** shown before connecting to a vehicle.
3. **Read-only by default.** Any action that *writes* to a vehicle (clear codes, program
   keys, flash a module) must go through `interface.WriteAction`, which requires a
   one-time confirmation token issued after the user explicitly confirms the action,
   the vehicle, and the risks. A module cannot skip this step.
4. Never run a write while the vehicle is moving; require ignition-on/engine-off where applicable.
