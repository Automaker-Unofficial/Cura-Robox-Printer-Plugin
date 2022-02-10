**G92** - Set X/Y/Z position to coordinates given . This command tells the software the location of the printhead - it is not necessarily the same as the physical position of the head.


**T0** - Tool 0 (Fine Nozzle - 0.3mm) . This command selects the fine printing nozzle.


**T1**  - Tool 1 (Fill Nozzle - 0.8mm) . This command selects the fill printing nozzle.


**M103** - First layer target temperature [S] S=Override Temperature °C . This command sets the nozzle temperature for the first layer of printing using data supplied from the reel EEPROM. [S] provides a manual override for custom temperature. e.g. M103 will set the nozzle temperature to the value stored on the reel / previous value sent, M103 S240 sets it to 

240°C.


**M104** - Set nozzle target temperature [S] S=Override Temperature °C for Nozzle 1 (Material 1 for SM/S2, Material 2 for DM) [T] T=Override Temperature °C for Nozzle 2 (Material 1 for DM, not used for S2/SM) . This command sets the nozzle temperature using data supplied from the reel EEPROM. [S] and/or [T] provides a manual override for custom temperature. e.g. M104 will set the nozzle temperature to the value stored on the reel / previous value sent, M104 S205 sets it to 205°C. To heat a dual material print head nozzle 1 to 230 C and nozzle 2 to 205 C, the command is M104 S230 T205.


**M105** - Show temperatures and PWM output, voltage detection. (T:aa @bb B:cc (^/$)dd A:ee *ff)  aa = Nozzle Temperature Setpoint (°C), bb = Nozzle Heater PWM (0-255), cc = Bed Temperature Setpoint (°C), dd = Bed Heater PWM (0-255) - ^ denotes 240V supply, and $ denotes 115V supply, ee = Ambient Temperature Setpoint (°C), ff = Ambient Fan PWM (0-255). This command shows the status of all heaters and temperature settings.


**M106** - Head Fan on [S] S=Speed (0-255) . This command sets the speed of the fan on the print head. e.g. M106 S255 sets the fan to 100% power, M106 S128 sets it to 50%.


**M107** - Head Fan off . This command turns off the head fan, but only if the nozzle temperature is lower than 60°C. The minimum fan speed if the nozzle temperature >60°C is 50% (S128).


**M109** - Wait for nozzle temperature to reach target . This command issues a stop to all commands until the nozzle reaches it’s target temperature.


**M114** - Display current position [X Y Z B] . This command displays the current position of all axes e.g. M104 will output all positions to the console in the form M104 X** Y** Z** B**.


**M84** - Turn off motors until next move . This disables all stepper motors until a G0 or G1 is sent.


**M92** - Set axis steps per unit [X Y Z E D B] . This command is only really for advanced use, as these values should never need to be changed. It sets how many microsteps are equivalent to one unit of motion i.e. for X, Y and Z, this is 1mm, for E and D, this is 1mm³ and for B this is the equivalent to the angle at full open.


**M113** - Show Z delta . This command displays the difference in height between the last two Z height probes.


**M115** - Show firmware version . Displays the firmware version which is installed on the Robox®.


**M119** - Show switch state [X Y Z Z+ E D B Eindex Dindex] . X = X Endstop, Y = Y Endstop, Z = Z Probe, Z+ = Z Top Endstop, E= Extruder 1 Output Switch, D = Extruder 2 Output  switch, B = Nozzle Homing Switch, Eindex = Extruder 1 Index Wheel, Dindex = Extruder 2 Index Wheel. This is provided for diagnostic purposes and shows the state of all switches on Robox®. e.g. M119 X:1 Y:0 Z:0 Z+:0 E:1 D:1 B:0 Eindex:0 Dindex:1 - 1 = Switch Closed, 0 = Switch Open


**M120** - Load filament [E D] . E = Extruder 1, D = Extruder 2. This executes the loading sequence for the specified extruder, however it is rarely required as this is triggered by movement of the indexing wheel when the output switch is open (i.e. no filament loaded).


**M121** - Unload filament [E D] . E = Extruder 1, D = Extruder 2. This executes the unloading sequence for the specified extruder when the output switch is closed (i.e. filament loaded).


**M128** - Head lights off . This turns the LEDs on the bottom of the printing head off.


**M129** - Head lights on . This turns the LEDs on the bottom of the printing head on.


**M139** - Set bed first layer target temperature [S] S=Override Temperature °C . This command sets the bed temperature for the first layer of printing using data supplied from the reel EEPROM. [S] provides a manual override for custom temperature. e.g. M103 will set the bed temperature to the value stored on the reel / previous value sent, M139 S100 sets it to 100°C.


**M140** - Set bed target temperature [S] S=Override Temperature °C . This command sets the nozzle temperature using data supplied from the reel EEPROM. [S] provides a manual override for custom temperature. e.g. M104 will set the bed temperature to the value stored on the reel / previous value sent, M140 S120 sets it to 120°C.


**M170** - Set ambient target temperature [S] S=Override Temperature °C . This command sets the ambient temperature using data supplied from the reel EEPROM. [S] provides a manual override for custom temperature. e.g. M104 will set the ambient temperature to the value stored on the reel / previous value sent, M170 S35 sets it to 35°C.


**M190** - Wait for bed temperature to reach target . This command issues a stop to all commands until the bed reaches it’s target temperature.


**M201** - Set maximum acceleration for moves [S] S=Acceleration in steps/s² . This command sets the maximum acceleration for ALL motion axes. Default is 12 steps/sec².


**M202** - Set maximum speeds [X Y Z E D] . This command sets the maximum speed of each axis, in it’s appropriate units. X, Y and Z are in mm/s, E and D are in mm³/s.


**M301** - Set nozzle heater parameters P, F, D, B, T, U . This command is only really for advanced use, as these values should never need to be changed. It is used to adjust the control parameters for the nozzle heaters.


**M302** - Set bed heater parameters P, F, D, B, T, U . This command is only really for advanced use, as these values should never need to be changed. It is used to adjust the control parameters for the bed heater.


**M303 - Set ambient temperature control parameters P, F, D, B, T, U .This command is only really for advanced use, as these values should never need to be changed. It is used to adjust the control parameters for the ambient fan.**


**M500** - Store parameters to EEPROM . This writes any new settings to the firmware. If not stored using M500, settings will be lost when the power is cycled.


**M502** - Revert to default parameter values . This resets the firmware parameters to the factory defaults. Save using M500.


**M503** - Show settings . This outputs the current firmware settings to the console.


**M510** - Invert axis [X Y Z E D B] . Where 0=false, 1=true. This command is only really for advanced use, as these values should never need to be changed. It causes all motion on the specified axis to occur in the opposite direction.


**M520** - Set axis travel [X Y Z] . This command is only really for advanced use, as these values should never need to be changed. It specifies the length of each axis in mm.


**M526** - Invert switch inputs [X Y Z Z+ E D B] . Where 0=false, 1=true. This command is only really for advanced use, as these values should never need to be changed. It inverts the output from the specified switch (X, Y, Z and Z+ endstops, extruder 1 and 2 output switches, nozzle homing switch).


**M527** -  Set home distance [X Y Z E D B] . This command is only really for advanced use, as these values should never need to be changed. For X, Y and Z, it specifies the distance the head can move beyond the point that the endstop is activated, and therefore it defines the homing speed. For E and D, this defines the distance filament travels from the extruder output switch to the entry point of the head along the Bowden tube.


**M906** - Set motor current [X Y Z E D B] . This command is only really for advanced use, as these values should never need to be changed. It sets the current of the specified motor in Amps. e.g. M906 X1.2 would set the X motor driver output to 1.2A.


**M907** - Set motor hold current (Amps) [X Y Z E D B] . This command is only really for advanced use, as these values should never need to be changed. It sets the hold current of the specified motor in Amps. e.g. M907 Z0.3 would set the Z motor driver hold output to 0.3A.


**M908** - Set extruder motor reduced current (Amps) [E D] . This command is only really for advanced use, as these values should never need to be changed. This sets the current of the extruder motor when a G36 command is issued - move until slip. This helps prevent ‘stripping’ of the filament by causing the motor to skip rather than the teeth skipping on the filament. e.g M908 E0.7 would set the extruder 1 slip current to 0.7A.


**M909** - Set filament slip detection threshold (mm) [S] . This command defines the difference between how far filament has been told to travel, and how far it travels in order to trigger a filament slip error. i.e. if this value is set to 2mm, and the filament is told to travel 10mm, a error will be triggered if it moves <8mm.