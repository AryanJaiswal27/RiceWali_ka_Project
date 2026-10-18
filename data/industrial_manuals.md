# [MANUAL: BOSCH_SHEM78]
## Equipment Specification: Bosch 800 Series / Ascenta Dishwasher
- Model Series: SHEM78****, SHPM78****, SHX878****
- Control Architecture: Power Module (Base Pan) + Operating Unit (Door Console)
- Active Board Revisions: Rev C / Rev E (Firmware MCU 4.18.2)
- Power Rating: 120V / 240V AC, 60 Hz, 12A Branch Circuit
- Wash Hydraulics: Dual BLDC Circulation & Drain Motors, Zeolite Thermal Drying Unit

### Safety Directives & Hazard Warnings
- **MANDATORY HAZARD WARNING (240V Base Pan Electrical Hazard):**
  The lower equipment base pan houses the main power module, BLDC circulation heat pump, drain pump, and flood float switch. Line voltage (120V/240V AC) is present on exposed spade terminals, PTC heater contacts, and interference suppressor capacitors. Always disconnect AC mains power at the breaker panel before removing the lower toe-kick access shroud or tilting the chassis.
- **Water Flood Boundary:**
  The expanded polystyrene (EPS) float disc in the base sump trough actuates an emergency safety microswitch upon 150 mL water accumulation. Continuous drain pump operation is commanded automatically regardless of door latch state.

### Diagnostic Procedures: Bosch SHEM78

#### Procedure BOSCH-HYD-01: Flood Float Actuation & Base Trough Isolation
- Target Subsystem: Hydraulic / Flood Safety
- Associated Error Codes: E15
- Step 1 (Non-Invasive Verification): Disconnect AC mains power. Verify that drain pump was running continuously with display showing E15. Inspect floor perimeter around toe-kick for water migration.
- Step 2 (Toe-Kick Access): Remove two Torx T20 screws securing outer steel toe-kick plate and acoustic insulation mat.
- Step 3 (Moisture Evacuation): Visually inspect lower condensation trough. If water is present, sponge or wet-vacuum standing water until base trough is dry and EPS float rests on base floor.
- Step 4 (Leak Path Inspection): Restore power briefly in diagnostic fill mode. Inspect water inlet valve solenoid threads, sump bowl perimeter silicone seal, and drain hose elbow for droplets.
- Step 5 [CRITICAL TECHNICIAN BOUNDARY - HALT]: If leak originates from circulation pump volute seal, cracked stainless tub seam, or lower water matrix assembly, replacement requires Authorized Field Technician with factory seal kit.

#### Procedure BOSCH-DRN-01: BLDC Drain Pump Impeller & Non-Return Valve Servicing
- Target Subsystem: Drainage
- Associated Error Codes: E24, E25
- Step 1 (Filter Assembly Extraction): Remove lower dish basket. Grasp stainless microfilter cylinder, rotate 90 degrees counter-clockwise, and lift out composite fine mesh screen. Clean debris under running hot water.
- Step 2 (Impeller Shroud Removal): Locate white plastic drain pump cover in sump recess. Release retaining clip or unfasten Torx T20 screw and pull cover forward and out.
- Step 3 (Impeller Inspection): Inspect 5-vane magnetic BLDC impeller. Remove glass splinters, toothpicks, bones, or twist ties wound around shaft. Verify impeller turns freely in 90-degree tactile magnetic steps.
- Step 4 (Non-Return Flapper Check): Check black rubber check valve flapper situated directly behind pump outlet. Verify flapper is supple, seats flat against orifice, and does not remain stuck open.
- Step 5 (Winding Resistance Measurement): Unplug drain pump 3-pin connector. Measure coil resistance across pins 1-2, 2-3, and 1-3 using digital multimeter. Nominal reading: 85 to 105 Ohms balanced.
- Step 6 [CRITICAL TECHNICIAN BOUNDARY - HALT]: If coil resistance is open (< 1 Ohm or > 200 Ohms) or power module triac drive is burned, pump replacement and control board flash requires Authorized Field Technician.

#### Procedure BOSCH-INV-01: Line Voltage Sag & Power Module Telemetry
- Target Subsystem: Inverter / Power Module
- Associated Error Codes: E27
- Step 1 (Supply Voltage Audit): Measure AC line voltage at supply receptacle under zero load (must be 120V AC +/- 10%).
- Step 2 (Branch Circuit Isolation): Verify appliance is not plugged into extension cords, multi-outlet tap adapters, or sharing circuit with high-wattage disposal or microwave.
- Step 3 (Junction Box Inspection): Check terminal block wiring connections in rear metal junction box. Tighten screw clamps and check for melted insulation.
- Step 4 (Active Load Measurement): Start Express cycle to energize 1400W flow-through heater. If line voltage drops below 98V AC during heating phase, external power grid impedance failure is confirmed.

#### Procedure BOSCH-OPT-01: AquaSensor Optical Turbidity Calibration
- Target Subsystem: Optical / Water Quality
- Associated Error Codes: Cleanliness Degradation / Cycle Extension
- Step 1 (Optical Prism Inspection): Locate AquaSensor dual infrared LED / phototransistor housing mounted in sump wall.
- Step 2 (Prism Cleaning): Wipe optical prism lens surface with isopropyl alcohol swab to remove calcium scale and fat film.
- Step 3 (Calibration Telemetry): Run Customer Service Test Program (hold keys 'A' + 'Start', power on). Select P1 (Sensor Calibration). Verify phototransistor optical transmission voltage reads between 3.8V and 4.6V DC in clear water.


---

# [MANUAL: WHIRLPOOL_WASHER_ALPHA]
## Equipment Specification: Whirlpool Front-Load Washer
- Platform Architecture: Alpha / Vertical Modular Washer (VMW) Front-Load Platform
- Technical Manual Reference: W11663204 Rev B
- Control Architecture: Appliance Control Unit (ACU) + Motor Control Unit (MCU)
- Active Board Revisions: Rev B3 / Rev C1 (ACU Part # W11419171)
- Drive System: 3-Phase Variable Frequency Brushless Direct Drive Induction / PMSM

### Safety Directives & Hazard Warnings
- **MANDATORY HAZARD WARNING (Direct-Drive Capacitor Discharge & 1200 RPM Spin-Basket Interlock):**
  The ACU and MCU inverter modules incorporate large high-voltage electrolytic smoothing capacitors (325V to 400V DC). Disconnect line power and wait a minimum of 3 minutes for capacitors to discharge through bleed resistors before touching control terminals or motor harness.
- **Spin-Basket Kinetic Interlock:**
  The wash basket rotates up to 1200 RPM, possessing severe kinetic energy. Never bypass the solenoid door lock switch (DL) or tamper with the bi-metal latch mechanism. Do not reach into tub until basket has come to a verified zero-RPM standstill.

### Diagnostic Procedures: Whirlpool Washer Alpha

#### Procedure WHRL-INV-01: Drive Motor Tachometer & Inverter Phase Verification
- Target Subsystem: Inverter / Drive Motor
- Associated Error Codes: F06 E01
- Step 1 (Capacitor Bleed-Down & Power Isolation): Unplug 120V power cord. Wait 3 full minutes. Remove rear sheet metal cabinet panel.
- Step 2 (Tachometer Harness Inspection): Inspect 3-wire tachometer sensor cable running from motor stator hub to MCU terminal connector J9. Verify no chafing against tub shock dampers.
- Step 3 (Mechanical Basket Drag Test): Rotate inner stainless basket slowly by hand. Verify smooth, quiet rotation without bearing rumble, spider arm binding, or clothing trapped between tub gasket.
- Step 4 (Tachometer Resistance Measurement): Disconnect connector J9 from MCU. Measure resistance between pins 1 and 2 (tachometer coil). Nominal specification: 115 to 130 Ohms at 20 C (68 F).
- Step 5 (Motor Stator Phase Balance): Measure 3-phase motor stator windings between MCU connector J6 pins (pins 1-2, 2-3, 1-3). Nominal specification: 8.5 to 14.0 Ohms balanced.
- Step 6 [CRITICAL TECHNICIAN BOUNDARY - HALT]: Motor stator core replacement, rotor magnet hub torqueing, or MCU board replacement requires Authorized Field Technician.

#### Procedure WHRL-HYD-01: Analog Pressure Sensor (APS) & Air Dome Integrity
- Target Subsystem: Hydraulic / Water Level
- Associated Error Codes: F03 E01
- Step 1 (Visual Tubing Inspection): Remove top cabinet lid (two 1/4-inch hex screws at rear). Locate Analog Pressure Sensor mounted on right chassis top rail.
- Step 2 (Pressure Tube Routing): Trace 1/4-inch clear vinyl pressure tube downward to the air dome chamber molded on lower outer tub sump. Verify tube has no pinch points, kinks, chafing, or water condensate traps.
- Step 3 (Air Dome Clearing): Detach vinyl tube from sensor nipple. Blow gently into tube to clear any trapped liquid detergent foam or lint sediment from the lower tub air bell dome.
- Step 4 (APS Voltage Telemetry): Reconnect tube ensuring airtight seal. Reconnect power and measure DC voltage across ACU J3 connector pins 1 and 3 (nominal 5.0 VDC reference).
- Step 5 [CRITICAL TECHNICIAN BOUNDARY - HALT]: If frequency output on J3-2 remains outside 20-46 kHz operating range or tub overfills, replacement of APS transducer requires Authorized Field Technician.

#### Procedure WHRL-THM-01: Wash Water Heating Element & Relay Telemetry
- Target Subsystem: Thermal
- Associated Error Codes: F08 E01
- Step 1 (Power Disconnect): Unplug washer from mains receptacle. Remove rear cabinet access panel.
- Step 2 (Terminal Inspection): Locate heating element base seated in lower rear tub cavity. Check terminal spade lugs for thermal discoloration, looseness, or scorched insulation.
- Step 3 (Heater Resistance Measurement): Disconnect both wire leads from element terminals. Measure element resistance using digital multimeter. Nominal specification: 12 to 18 Ohms for 120V element. Infinite resistance indicates open-circuit heating element.
- Step 4 (Ground Fault Isolation): Measure resistance between each heater pin and tub chassis ground lug (must be > 10 Megohms).
- Step 5 [CRITICAL TECHNICIAN BOUNDARY - HALT]: Replacing ruptured tubular heating element, sealing NBR compression gasket, or replacing ACU heater power relay requires Authorized Field Technician.

#### Procedure WHRL-DRN-01: Eco-Drain Pump & Coin Trap Cleanout
- Target Subsystem: Drainage
- Associated Error Codes: F09 E01, Long Drain
- Step 1 (Drain Water Evacuation): Place low-profile pan beneath lower front service door. Uncap small auxiliary drain hose and drain residual sump water.
- Step 2 (Coin Trap Extraction): Unscrew large round coin trap filter plug counter-clockwise. Pull assembly straight out.
- Step 3 (Impeller Clearance): Clean coins, hairpins, and lint cakes from filter basket. Reach into pump housing bore and confirm impeller rotates freely with magnetic pulsing.


---

# [MANUAL: LG_REFRIG_LFXS]
## Equipment Specification: LG Smart French-Door Refrigerator
- Model Series: LFXS26973*, LRFCS2503*, LFXC24796*
- Compressor Architecture: Linear Inverter Compressor (FLB075LANA / FLA108LANA)
- Control Architecture: Micom Main Inverter Control Board (EBR Series)
- Active Board Revisions: Rev 4.2 / Rev 5.0 (EBR822304*)
- Refrigerant Charge: R600a (Isobutane) - 52g / 1.83 oz hermetic charge

### Safety Directives & Hazard Warnings
- **MANDATORY HAZARD WARNING (Flammable R600a Isobutane Refrigerant Isolation):**
  This equipment utilizes hydrocarbon refrigerant R600a (Isobutane), an EPA ASHRAE Class A3 flammable gas. Brazing or opening the sealed refrigeration loop with open flames is strictly prohibited. Only use certified explosion-proof vacuum pumps, R600a recovery equipment, and ultrasonic / Lokring flameless tube fittings. Work area must maintain continuous forced ventilation.
- **3-Minute PCB Bleed-Down Delay:**
  The Inverter Compressor Drive PCB operates on high-voltage DC (up to 450V DC across electrolytic filter reservoir). Wait a minimum of 3 minutes after AC power disconnect to allow bleeder resistors to discharge capacitors before servicing electrical components.

### Diagnostic Procedures: LG Refrigerator LFXS

#### Procedure LG-INV-01: Inverter Linear Compressor 5-Blink Locked Rotor Isolation
- Target Subsystem: Inverter / Sealed System
- Associated Error Codes: BLNK-5
- Step 1 (Bleed-Down & LED Diagnosis): Unplug refrigerator. Wait 3 minutes. Remove metal rear machine compartment cover. Restore power and observe the red diagnostic LED on the Main Inverter Board. Confirm 5 blinks followed by 2-second pause.
- Step 2 (Compressor Terminal Access): Disconnect power again. Remove plastic terminal cover from linear compressor housing.
- Step 3 (Stator Resistance Measurement): Unplug compressor harness. Measure resistance across linear compressor terminal pins U and V. Nominal specification: 6.0 to 11.0 Ohms at room temperature (25 C / 77 F).
- Step 4 (Stator Ground Isolation): Measure resistance between compressor terminal pins and bare copper compressor suction stub (must exceed 5 Megohms).
- Step 5 (Discharge Stroke Inspection): Inspect compressor spring suspension mounts. If stator coil measures normal (6-11 Ohms) but compressor buzzes and fails to reciprocate, internal piston / spring failure is confirmed.
- Step 6 [CRITICAL TECHNICIAN BOUNDARY - HALT]: Linear compressor replacement requires EPA Universal Certified Technician licensed for flammable R600a evacuation, nitrogen sweep, and flameless Lokring mechanical crimping.

#### Procedure LG-INV-02: Intelligent Power Module (IPM) 6-Blink Overcurrent Isolation
- Target Subsystem: Inverter / Motor Drive
- Associated Error Codes: BLNK-6
- Step 1 (Condenser Fan Inspection): Observe condenser cooling fan adjacent to compressor. Verify fan blade is not obstructed by pet hair, lint blankets, or wire harness bundle.
- Step 2 (Condenser Coil Cleaning): Clean wire tube condenser grid using soft brush and HEPA vacuum nozzle.
- Step 3 (Inverter PCB Heat Sink Check): Inspect IPM aluminum heat sink on Main PCB. Check for loose clamp screws or thermal compound degradation.
- Step 4 (Compressor Overload Relay Check): Test OLP (Overload Protector) snapped onto compressor body with multimeter (must read < 0.5 Ohms closed).
- Step 5 [CRITICAL TECHNICIAN BOUNDARY - HALT]: If IPM transistors are shorted or PCB gate drive is damaged, board replacement requires Authorized Field Technician.

#### Procedure LG-THM-01: Evaporator Defrost Circuit & Sheath Heater Diagnosis
- Target Subsystem: Thermal / Defrost
- Associated Error Codes: DH-ERR
- Step 1 (Frost Pattern Inspection): Remove freezer drawers and rear interior plastic cover panel. Inspect evaporator fins for solid ice block or frost choke.
- Step 2 (Defrost Heater Resistance): Unplug white 2-pin connector feeding the aluminum defrost sheath heater. Measure resistance across heater element leads. Nominal specification: 80 to 120 Ohms. Infinite reading indicates burned heater element.
- Step 3 (Thermal Bimetal Safety Fuse Test): Measure continuity across orange/brown wires of the defrost bimetal thermal protector clipped to upper evaporator tube. Must be 0 Ohms (closed) when chilled below 0 C (32 F).
- Step 4 (Defrost Thermistor Resistance): Measure defrost NTC sensor resistance. Specification: 30k Ohms at 0 C (32 F), 10k Ohms at 25 C (77 F).
- Step 5 [CRITICAL TECHNICIAN BOUNDARY - HALT]: If heater and fuses test normal, defrost relay drive on Main Micom PCB has failed and requires Authorized Field Technician for board replacement.

#### Procedure LG-HYD-01: Dual Water Valve Solenoid & Ice Maker Fill Circuit
- Target Subsystem: Hydraulic / Water Dispenser
- Associated Error Codes: Ice Maker Timeout / Water Drip
- Step 1 (Water Pressure Verification): Verify home supply water pressure to refrigerator is between 20 and 120 PSI.
- Step 2 (Solenoid Coil Resistance): Disconnect primary and secondary water inlet valve electrical connectors. Measure coil resistance on each solenoid. Nominal specification: 180 to 240 Ohms for primary, 350 to 450 Ohms for secondary.


---

# [MANUAL: BREVILLE_BES920]
## Equipment Specification: Breville Dual Boiler Espresso Machine
- Model Series: BES920XL, BES980XL (Oracle Series)
- Boiler Architecture: Dual Independent Stainless Steel Boilers (Brew Boiler: 0.3L, Steam Boiler: 0.9L)
- Control Architecture: Dual PID Microprocessor Controller with Solid State Relays (SSR)
- Active Board Revisions: Rev 3.4 / Rev 4.1 (Main Power Board + Digital Display Logic PCB)
- Operating Pressures: 15-Bar ULKA Vibratory Pumps with Over-Pressure Valve (OPV calibrated to 9.5 Bar)

### Safety Directives & Hazard Warnings
- **MANDATORY HAZARD WARNING (15-Bar Pressurized Steam Boiler Scalding & Brass Solenoid Boundary):**
  The steam boiler operates at 135 C to 140 C (275 F to 284 F) under 2.5 to 3.0 bar continuous steam pressure, while espresso extraction generates up to 15 bar hydraulic pressure. Opening boiler probe fittings, brass solenoid valves, or Teflon PTFE tube collars on energized or hot equipment will discharge superheated steam and boiling water causing severe scalding.
- **Mandatory Depressurization & Cool-Down:**
  Before servicing any hydraulic, thermal, or solenoid components, disconnect AC mains plug, allow machine to cool down completely (minimum 45 minutes), and vent steam boiler by opening manual brass ball drain valves on lower rear chassis using a flat screwdriver into a heat-resistant container.

### Diagnostic Procedures: Breville Dual Boiler BES920

#### Procedure BREV-HYD-01: Steam Boiler Fill Timeout & Level Probe Maintenance
- Target Subsystem: Hydraulic / Boiler Fill
- Associated Error Codes: Er01
- Step 1 (Water Reservoir Seating): Verify water tank is filled with cold filtered water (TDS 50-100 ppm). Check that magnetic reed float in water tank vertical channel floats freely to top.
- Step 2 (Tank Valve Mesh Inspection): Inspect silicone intake valve in machine base. Clean stainless steel filter screen of scale buildup or algae film.
- Step 3 (Boiler Drain Valve Check): Verify rear manual boiler brass drain valve petcocks are turned fully horizontal (closed). If valves weep, replace internal silicone O-rings (size 007).
- Step 4 (Conductive Level Probe Inspection): Remove top machine cover (6 Torx T10 screws). Locate steam boiler top flange. Inspect white conductive water level probe wires. Verify push-on spade terminals are tight and free of green verdigris copper oxide.
- Step 5 (ULKA Pump Prime Test): Power on machine. Listen for vibratory fill pump hum. If pump hums loudly without pumping water, attach silicone syringe to water inlet socket and force prime 30 mL water while pump runs.
- Step 6 [CRITICAL TECHNICIAN BOUNDARY - HALT]: If 2-way brass water fill solenoid fails to open (coil resistance outside 1.2k - 1.8k Ohms) or boiler scale requires chemical descaling teardown, service requires Authorized Field Technician.

#### Procedure BREV-THM-01: Grouphead Thermal Runaway & Temperature Sensing
- Target Subsystem: Thermal / Grouphead
- Associated Error Codes: Er02
- Step 1 (Immediate Power Disconnection): Unplug machine immediately from wall outlet. Allow machine to cool completely to room temperature.
- Step 2 (Chassis Cover Removal): Remove top lid and inspect grouphead cast brass assembly.
- Step 3 (NTC Harness Inspection): Inspect 2-wire silicone harness connecting grouphead NTC thermistor to main control PCB. Check for pinched wires or damaged heat-shrink insulation resting against brass boiler.
- Step 4 (NTC Resistance Measurement): Disconnect grouphead NTC connector from logic board. Measure resistance across thermistor pins. Nominal specification: 50k Ohms at 25 C (77 F), dropping to ~5.5k Ohms at 93 C (200 F).
- Step 5 (Solid State Relay SSR Test): Inspect grouphead SSR located on rear mounting bracket. Test for shorted triac output. If triac has failed shorted, 120V is continuously applied to grouphead cartridge heater regardless of temperature.
- Step 6 [CRITICAL TECHNICIAN BOUNDARY - HALT]: SSR module replacement, brass grouphead heating element extraction, or micro-controller board replacement requires Authorized Field Technician.

#### Procedure BREV-THM-02: Steam Boiler NTC Open Circuit Diagnosis
- Target Subsystem: Thermal / Steam Generation
- Associated Error Codes: Er03
- Step 1 (Power Disconnect & Depressurization): Disconnect AC power plug. Verify pressure gauge reads 0 bar.
- Step 2 (Harness Seating): Remove top cover. Locate 2-pin connector labeled 'NTC-STM' on Main Power Board. Ensure connector latch is fully engaged.
- Step 3 (Sensor Resistance Measurement): Disconnect NTC-STM plug. Measure resistance directly across pins. Nominal specification: 50k Ohms at 25 C (77 F). An infinite or mega-ohm reading confirms open circuit thermistor bead or fractured internal lead.
- Step 4 [CRITICAL TECHNICIAN BOUNDARY - HALT]: Extracting threaded NTC sensor probe from pressurized steam boiler shell requires high-temperature food-grade PTFE thread sealant and torque calibration by Authorized Field Technician.

#### Procedure BREV-HYD-02: 3-Way Group Solenoid Valve & Pressure Exhaust
- Target Subsystem: Hydraulic / Pressure Relief
- Associated Error Codes: Brew Pressure Loss, Dripping Grouphead
- Step 1 (Over-Pressure Valve Audit): Install blind rubber backflush disc into 58mm portafilter. Lock into grouphead and press Manual Shot.
- Step 2 (Pressure Gauge Reading): Observe analog front pressure gauge. Pressure must ramp smoothly to 9.5 Bar.
- Step 3 (Solenoid Exhaust Inspection): At end of shot, verify 3-way solenoid opens with distinct click and discharges 15-20 mL water into front drip tray.
- Step 4 (De-scale Routine): If 3-way solenoid stutters or drips continuously, execute backflush cleanout with espresso detergent tablet.
