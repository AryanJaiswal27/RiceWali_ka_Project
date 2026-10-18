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

---

# Consumer Appliance & Household Electronics Field Maintenance Standard
### Standard Reference: APPL-HOME-2026-V1 // Diagnostic & Operational Safety Manual

---

## Home Split AC Cooling & Gas Leak Troubleshooter

### Procedure AC-01: Evaporator De-Icing and Airflow Verification
**Applicable Equipment:** Inverter & Fixed-Speed Residential Split Air Conditioning Systems  
**Disruption Level:** Non-Disruptive (Operator Level)  
**Safety Threshold:** Ensure power isolator switch is accessible before accessing outdoor unit.

1. **Defrost Cycle Execution:** Switch AC to Fan-Only mode for 30 minutes to melt any ice buildup across the aluminum fins of the indoor evaporator coil without applying artificial heat.
2. **Filter Maintenance:** Open the indoor unit front panel, slide out the nylon washable dust filters, and rinse under warm water. Allow filters to dry thoroughly before reinstallation.
3. **Condenser Clearance:** Inspect the outdoor condenser unit. Ensure a minimum of 30cm clearance from rear walls and 1 meter from front exhaust. Clear leaves, lint, and garden debris from outdoor coil fins.
4. **Airflow Temperature Differential:** Using a digital thermometer, record return air temperature and supply air temperature at the indoor louvers. A healthy refrigeration cycle yields an 8 C to 12 C delta under steady state.

### Procedure AC-02: Refrigerant Suction Pressure & Leak Isolation
**Applicable Equipment:** R32 / R410A Split Inverter Refrigerant Circuits  
**Disruption Level:** Low-Disruption to Service-Affecting  
**Safety Threshold:** R32 is mildly flammable (A2L classification). No open flames or smoking near service valves.

1. **Soap Bubble Leak Isolation:** Apply soapy water solution or professional bubble leak detector to indoor flare nuts and outdoor brass service ports. Inspect for growing bubbles indicating active gas discharge.
2. **Suction Pipe Temperature Audit:** Observe the brass suction (thick pipe) and liquid (thin pipe) service valves while running in Cool Mode at 16 C:
   - If the thin liquid line is frosted, refrigerant undercharge / gas leak is confirmed.
   - If the thick suction line is cold and sweating with droplets, gas volume is within normal parameters.
3. **Vapor Pressure Verification:** Certified HVAC Technician connects digital manifold gauges:
   - R32 nominal suction pressure: 115 - 135 PSI.
   - R410A nominal suction pressure: 110 - 130 PSI.
   - Subcooling target: 5K to 8K.
4. **Mandatory Safety Halt:** If suction pressure reads below 70 PSI, evacuate system, perform 24-hour nitrogen pressure-decay test (450 PSI), repair leaks, and vacuum to 500 microns before precision weighing of factory refrigerant charge.

### Procedure AC-03: Inverter Compressor IPM & Electronic Expansion Valve (EEV) Servicing
**Applicable Equipment:** Inverter Power Module (IPM) & BLDC Rotary Compressor  
**Disruption Level:** Critical Invasive (Certified HVAC Technician Required)  
**Safety Threshold:** DC bus capacitor retains 380V DC for 5 minutes post-power disconnection.

1. **Power Isolation:** Trip the outdoor breaker and wait 5 minutes. Verify 0V across DC bus capacitors with a 600V CAT-III multimeter.
2. **Compressor Motor Winding Test:** Disconnect U, V, and W compressor leads. Measure resistance between U-V, V-W, and U-W. All three readings must be balanced within +/- 0.1 Ohm (typically 0.8 - 1.5 Ohms). Check resistance to ground (must exceed 20 Megaohms).
3. **EEV Solenoid Check:** Measure resistance of Electronic Expansion Valve stepper coil leads (typically 46 Ohms per phase). Verify valve clicks upon power-up initialization.

---

## Front-Load Washing Machine Motor & Drain Pump Assistant

### Procedure WM-01: Emergency Drainage & Coin Trap Servicing
**Applicable Equipment:** Front-Load Inverter Washing Machines  
**Disruption Level:** Non-Disruptive (Operator Level)  
**Safety Threshold:** Ensure machine is unplugged from 230V mains socket before servicing filter.

1. **Water Isolation:** Turn off cold and hot water supply inlet taps. Disconnect electrical plug.
2. **Emergency Hose Drainage:** Open the bottom-right front service access flap. Place a shallow baking pan or towel on the floor. Unclip the black rubber emergency drain tube, remove the stopper plug, and allow standing water to drain into the pan.
3. **Coin Trap Filter Cleaning:** Slowly rotate the cylindrical debris filter counter-clockwise. Pull out the filter assembly and remove trapped debris: coins, safety pins, hair clips, and lint pellets. Rinse filter under running water.
4. **Impeller Freedom Inspection:** Use a flashlight to inspect the pump cavity. Use a pencil or finger to rotate the plastic impeller cross. It should rotate with magnetic stepping resistance (quarter-turn clicks) without binding.

### Procedure WM-02: BLDC Direct Drive Hall Sensor & Drum Bearing Check
**Applicable Equipment:** Direct-Drive Inverter Motors & Spider Drum Assemblies  
**Disruption Level:** Low-Disruption to Hardware Isolation  
**Safety Threshold:** Do not touch energized stator coils. Disconnect mains before removing rear access panel.

1. **Manual Drum Spin Test:** Open front door and spin the stainless drum rapidly by hand:
   - If drum makes a loud rumbling / jet-engine noise, the tub spider bearing and shaft seal are degraded.
   - If drum wobbles vertically with play when lifted from top lip, rear tub bearing replacement is required.
2. **Hall Sensor Tachometer Verification:** If motor judders or shows Error LE/3E, inspect the 4-pin hall effect sensor mounted on the stator. Verify 5V DC supply and toggle voltage on pins while slowly rotating rotor.
3. **Rotor Hub Nut Torque:** Inspect center 17mm/19mm rotor retaining nut. Ensure torque specification (88-100 Nm) with thread locker intact.

### Procedure WM-03: Door Interlock PTC Switch & Triac Diagnostics
**Applicable Equipment:** Thermal PTC Solenoid Door Lock Mechanisms  
**Disruption Level:** Hardware Isolation (Technician Required for Internal Panel Teardown)  
**Safety Threshold:** PTC door interlock carries live 230V AC mains potential.

1. **Door Latch Mechanical Audit:** Inspect the metal door latch hook on the inner door glass. Verify that return spring holds the hook level and latches securely into the chassis strike.
2. **PTC Resistance Test:** Disconnect 3-wire plug to door switch. Measure resistance across PTC bi-metal terminals (typically 800 - 1500 Ohms at 25 C).
3. **Triac Drive Verification:** If door lock beeps dE despite new switch, check main control board triac Q1 for short-circuit or burning on printed copper traces.

---

## Smartphone Screen & Battery Replacement Safety Guide

### Procedure SP-01: Swollen Lithium Battery Emergency Isolation & Pouch Handling
**Applicable Equipment:** Lithium-Ion / Lithium-Polymer Pouch Cells  
**Disruption Level:** Critical Invasive Safety Hazard  
**Safety Threshold:** CRITICAL DANGER: Puncturing or bending a swollen lithium battery causes spontaneous combustion, 800 C thermal runaway, and toxic hydrofluoric gas release.

1. **Immediate Quarantine:** If screen or back glass is lifting due to swollen battery, disconnect charger instantly and power off device. Do not apply pressure or attempt to snap glass back into bezel.
2. **Fire-Safe Depository:** Place quarantined phone on a ceramic tile surface or inside a steel ammo can / sand bucket away from paper, wood, and curtains.
3. **Extraction Safety Protocol (Authorized Device Technician):**
   - Wear safety goggles and heat-resistant nitrile gloves.
   - Do NOT use metal pry tools, razor blades, or heat guns exceeding 65 C.
   - Apply 3-5 drops of 99% isopropyl alcohol around adhesive pull tabs to dissolve acrylic pressure-sensitive adhesive.
   - Pull stretch-release adhesive strips horizontally without snapping.
   - Store depleted swollen cell in Class D fire-safe bucket for hazardous e-waste recycling.

### Procedure SP-02: AMOLED Digitizer Replacement & Display FPC Seating
**Applicable Equipment:** Flexible AMOLED / OLED Display Substrates  
**Disruption Level:** Hardware Isolation (Technician Level)  
**Safety Threshold:** Wear grounded ESD wrist strap (1 Megaohm resistor) to protect sensitive display driver ICs.

1. **Pre-Installation Test:** Before applying frame adhesive, connect display FPC flex cable to motherboard logic board. Reconnect battery last. Power on device to test touch response, multi-touch gestures, and color uniformity.
2. **FPC Connector Inspection:** Inspect gold micro-pins on motherboard display header using 20x stereo microscope. Ensure zero bent pins, lint, or flux contamination.
3. **Frame Cleaning & Adhesive Laydown:** Scrape off old black foam adhesive from chassis aluminum frame using plastic spudger. Wipe frame with alcohol. Apply precision pre-cut perimeter adhesive gasket. Press display evenly with padded clamping tools for 20 minutes.

### Procedure SP-03: USB-C Charging Port Debris Removal & Moisture Reset
**Applicable Equipment:** USB Type-C & Lightning Dock Assemblies  
**Disruption Level:** Non-Disruptive (Operator Level)  
**Safety Threshold:** Never insert conductive metal needles, paperclips, or safety pins into the charging port.

1. **Lint Debris Extraction:** Inspect port with concentrated LED light. Using a carved, non-conductive wooden toothpick or plastic dental pick, gently sweep along the bottom of the cavity around the center tongue. Extract packed pocket lint.
2. **Moisture Sensor Dryout:** If "Liquid Detected in Charging Port" alert persists, stand phone upright with port facing downward over a paper towel in a dry, ventilated room for 4 hours. Do not use compressed air cans or hair dryers.
3. **Cable Gold Pin Verification:** Inspect USB-C cable connector. Ensure VBUS and CC contact pins are not blackened by electrical arcing. Replace damaged charging cables immediately.

---

## Automatic Espresso Coffee Machine Descaling & Pressure Assistant

### Procedure CF-01: Thermocoil Hydraulic Descaling & Flow Meter Calibration
**Applicable Equipment:** Residential Thermocoil & Dual Boiler Espresso Machines  
**Disruption Level:** Non-Disruptive (Operator Level)  
**Safety Threshold:** Hot water and descaling acid operate at 95 C. Wear protective kitchen gloves to prevent splash burns.

1. **Resin Filter Removal:** Remove water reservoir and discard old softening resin cartridge. Rinse tank thoroughly.
2. **Acid Solution Preparation:** Dissolve food-grade descaling powder (citric acid or sulfamic/lactic acid) into 1.5 liters of warm water per manufacturer dosage. Never use vinegar as it degrades silicone EPDM O-rings.
3. **Descaling Cycle Execution:** Start automated descale sequence. The machine cycles pump for 20 seconds, pauses for 30 seconds to allow acid scale breakdown in thermocoil tubes, then repeats until tank is empty.
4. **Clean Water Rinse Flush:** Fill tank with fresh filtered water and run 2 full reservoirs through both the group head and steam wand to eliminate residual acid odor.

### Procedure CF-02: 15-Bar Vibration Pump & Overpressure Valve (OPV) Tuning
**Applicable Equipment:** Ulka Vibration Pumps (EP5 / EAX5) & Adjustable Brass OPVs  
**Disruption Level:** Hardware Isolation (Technician Level)  
**Safety Threshold:** Vibration pump operates on live 230V AC; water lines operate under 15 bar pressure.

1. **Blind Basket Pressure Measurement:** Insert solid blind rubber disc into 58mm portafilter. Lock into group head and engage pump.
2. **Pressure Gauge Audit:**
   - Target nominal extraction pressure: 9.0 to 9.5 Bar.
   - If gauge pins above 15 Bar, the OPV silicone seat is stuck with mineral debris.
   - If gauge fails to rise above 4 Bar, internal pump Teflon check ball is worn.
3. **OPV Adjustment:** Turn brass hex screw on overpressure valve counter-clockwise to reduce bypass pressure until gauge reads steady 9.2 Bar while pumping against blind basket.

### Procedure CF-03: Conical Burr Grinder Jam Clearing & Zero-Point Calibration
**Applicable Equipment:** Hardened Steel 40mm Conical Burrs & Planetary Gear Reduction  
**Disruption Level:** Low-Disruption (Operator Level)  
**Safety Threshold:** Unplug machine before reaching into grinder throat. Steel burr edges are razor sharp.

1. **Hopper Removal:** Close bean hopper gate, twist counter-clockwise, and remove hopper. Empty beans into a bowl.
2. **Upper Burr Extraction:** Lift metal wire handle on top burr assembly and turn counter-clockwise until indexing dots align. Lift burr vertically out of housing.
3. **Chamber Vacuum:** Vacuum ground coffee residue from bottom burr chamber. Use brass wire brush to clean compacted oily coffee fines from burr cutting flutes.
4. **Foreign Object Inspection:** Check for unroasted green beans, small pebbles, or wood chips that wedged between burr teeth. Reassemble upper burr and test grind on coarse setting before returning to espresso fine.

---

## Home RO Water Purifier Filter & Membrane Monitor

### Procedure RO-01: Pre-Filter Spun Polypropylene & Carbon Block Flushing
**Applicable Equipment:** Multi-Stage Domestic Reverse Osmosis Systems (50 / 75 / 100 GPD)  
**Disruption Level:** Non-Disruptive (Operator Level)  
**Safety Threshold:** Relieve internal water line pressure before unscrewing filter housings.

1. **Inlet Water Cutoff:** Turn off the 1/4-inch chrome ball valve connecting feed line to main plumbing. Depress faucet lever to bleed pressure until water stops dripping.
2. **Housing Spanner Wrenching:** Position bucket under pre-filter housing. Use circular plastic spanner wrench to loosen housing clockwise (from top view).
3. **Sediment Cartridge Inspection:** Extract 5-micron spun polypropylene cartridge. If outer layer is coated in reddish-brown clay/rust, replace cartridge. Clean interior bowl with sponge.
4. **Carbon Block Flush:** When installing new carbon block, disconnect downstream tubing to RO membrane. Direct flow into bucket and flush 5 liters of water to purge carbon black powder fines before reconnecting to membrane stage.

### Procedure RO-02: Reverse Osmosis Membrane TDS Rejection & Auto-Flush Solenoid Audit
**Applicable Equipment:** Polyamide Thin-Film Composite (TFC) RO Membranes  
**Disruption Level:** Low-Disruption  
**Safety Threshold:** Discard first 2 tanks of purified water after installing fresh RO membrane.

1. **Digital TDS Benchmark:** Use calibrated digital TDS meter to measure raw inlet tap water (e.g., 400 PPM). Measure pure output water from faucet. Healthy TFC membrane achieves 90% to 95% rejection (output < 40 PPM).
2. **Auto-Flush Solenoid Operation:** Power cycle system. Listen for the auto-flush solenoid clicking open for 18-30 seconds, generating high-velocity wastewater bypass across membrane leaf to purge mineral scaling.
3. **Flow Restrictor (FR) Matching:** Verify wastewater flow restrictor matches membrane capacity:
   - 50 GPD membrane requires FR-350 or FR-450.
   - 75 GPD membrane requires FR-450 or FR-550.
   - 100 GPD membrane requires FR-650.
   If restrictor is blocked, membrane fouls with calcium within 30 days.

### Procedure RO-03: High-Pressure Cutoff Switch & Leak Sensor Recovery
**Applicable Equipment:** High-Pressure Auto-Shutoff Switches & Base Leak Detectors  
**Disruption Level:** Low-Disruption (Operator Level)  
**Safety Threshold:** Keep 24V DC transformer adapter dry during troubleshooting.

1. **Leak Pad Inspection:** If machine emits continuous beeping and halts booster pump, inspect bottom chassis tray for pooled water.
2. **Push-Fit Collet Tightening:** Inspect all 1/4-inch and 3/8-inch push-fit JG fittings. Ensure tubing ends are cut at 90-degree angle without burrs and fully inserted past inner O-ring (approx. 18mm depth). Ensure blue horseshoe locking clips are in place.
3. **High-Pressure Switch Check:** Close storage tank valve. Within 60 seconds, booster pump should turn off automatically as line pressure reaches 40 PSI. If pump runs continuously, replace high-pressure microswitch.

---

## Electric Scooter Throttle & Charger Diagnostic Tool

### Procedure ES-01: Hall Sensor Throttle Voltage Sweep (0.8V - 4.2V)
**Applicable Equipment:** 36V / 48V Light Electric Commuter Scooters  
**Disruption Level:** Non-Disruptive to Low-Disruption  
**Safety Threshold:** Prop scooter on center stand with drive wheel suspended in the air before testing throttle.

1. **Throttle Return Spring Inspection:** Press thumb throttle lever fully and release. Verify that spring snaps lever back to idle instantly without sticking against rubber handlebar grip.
2. **Julet Connector Inspection:** Locate the circular 3-pin waterproof connector on handlebar harness. Unthread collar and inspect gold pins for oxidation, moisture, or misalignment.
3. **Analog Voltage Verification:** Using a digital multimeter, probe ground (black) and signal (green/blue) wires with power ON:
   - Idle position: Must read 0.8V to 1.0V DC.
   - Fully depressed position: Must read 4.0V to 4.2V DC.
   - If voltage stays at 0.0V or 5.0V, Hall sensor element or magnet inside throttle assembly is dislodged.

### Procedure ES-02: Lithium BMS Charging Interlock & Temperature Sensor Audit
**Applicable Equipment:** 10S / 13S Lithium-Ion Battery Packs with Smart BMS  
**Disruption Level:** Critical Invasive Safety Hazard (Certified EV Technician Required)  
**Safety Threshold:** Never pierce, compress, or submerge lithium battery packs. Fire hazard requires Class D extinguisher.

1. **Charger Port Pin Inspection:** Inspect cylindrical charging socket on scooter deck. Check for copper verdigris corrosion, lint, or blackened ground pins caused by plug-in spark.
2. **Charger Voltage Check:** Plug charger into mains wall socket (unconnected to scooter). Measure DC output plug with multimeter:
   - 36V battery pack charger: Nominal 42.0V DC (+/- 0.2V).
   - 48V battery pack charger: Nominal 54.6V DC (+/- 0.3V).
3. **BMS Thermal Lockout Reset:** If charger flashes red/green and battery was recently ridden in cold (< 0 C) or hot (> 40 C) weather, allow scooter to stabilize at 22 C for 2 hours before reconnecting charger.

### Procedure ES-03: Hub Motor Phase Line Resistance & Controller MOSFET Isolation
**Applicable Equipment:** Brushless DC (BLDC) Geared / Direct Drive Wheel Motors  
**Disruption Level:** Hardware Isolation (Technician Level)  
**Safety Threshold:** Disconnect battery main XT60 connector before probing motor controller.

1. **Manual Spin Resistance Check:** Turn scooter power completely OFF. Spin motor wheel by hand:
   - If wheel spins freely, mechanical bearings are sound.
   - If wheel stutters with heavy magnetic cogging resistance even with power OFF, motor phase wires are shorted together.
2. **Phase Wire Disconnection Test:** Unplug the 3 heavy gauge motor phase bullet connectors (Yellow, Green, Blue) from the motor controller:
   - If wheel now spins freely, motor windings are healthy and the motor controller has blown low-side MOSFET transistors.
   - If wheel still resists rotation, phase wires are melted together inside motor axle shaft.

---

## Microwave Oven Magnetron & Door Interlock Safety Assistant

### Procedure MW-01: Primary & Secondary Safety Door Interlock Verification
**Applicable Equipment:** Countertop & Built-in Residential Microwave Ovens  
**Disruption Level:** Non-Disruptive (Operator Level)  
**Safety Threshold:** Ensure oven is unplugged before touching door hinges or latch mechanisms.

1. **Latch Hook Integrity:** Inspect the two plastic door latch prongs protruding from inner door perimeter. Verify that neither hook is cracked, bent, or chipped.
2. **Door Alignment & Gap Audit:** Close door and measure gap between door gasket and oven face. Gap must be under 1.5mm uniform along all four edges to prevent microwave leakage.
3. **Audible Microswitch Verification:** Listen carefully as door is closed slowly. You must hear two distinct clicks: first the primary safety switch, followed immediately by the monitor/secondary switch. If only one click is audible, interlock bracket requires realignment.

### Procedure MW-02: High-Voltage Waveguide Mica Inspection & Magnetron Arc Isolation
**Applicable Equipment:** 2.45 GHz Cavity Waveguide & Mica Sheets  
**Disruption Level:** Non-Disruptive (Operator Level)  
**Safety Threshold:** Unplug oven immediately if loud buzzing or arcing sparks are observed in cavity.

1. **Waveguide Cover Inspection:** Locate the thin silver/brown mica mineral sheet mounted on the right interior cavity wall.
2. **Carbonization Check:** Inspect mica sheet for black scorch marks, burnt holes, or grease deposits. Food splatter absorbs microwave energy, superheats, and causes plasma arcing.
3. **Mica Sheet Replacement:** Unscrew plastic retaining rivet. Pull out old scorched mica sheet. Clean underlying stainless steel waveguide opening with alcohol. Insert brand new pre-cut mica sheet and re-pin rivet.

### Procedure MW-03: Lethal High-Voltage Capacitor Grounding & Diode Check
**Applicable Equipment:** High Voltage (HV) Transformer, 2100V AC Capacitor & HV Rectifier Diode  
**Disruption Level:** Critical Invasive Safety Hazard (Certified Appliance Technician Mandatory)  
**Safety Threshold:** DEADLY HAZARD: The HV capacitor retains 2,200V to 4,000V DC at lethal current even when the oven has been unplugged for weeks. Non-technicians must NEVER remove the outer metal housing.

1. **Safety Grounding Protocol:** Certified Technician unplugs oven, wears 10kV dielectric insulated gloves, and connects a 20kV grounding discharge probe (with built-in 20-watt 20k-Ohm ceramic resistor) across both terminals of the HV capacitor to chassis ground for 10 seconds.
2. **HV Diode Meter Test:** Measure HV rectifier diode with 9V battery circuit or dedicated high-voltage diode tester. Standard multimeter diode check (2V) will read open in both directions due to forward voltage drop (~6V).
3. **Transformer Secondary Windings:** Measure resistance of transformer secondary high-voltage winding to chassis ground (nominal 80 to 120 Ohms).

---

## Home 3D Printer Bed Leveling & Nozzle Clog Troubleshooter

### Procedure 3D-01: Hotend Nozzle Cold Pull & Extruder Gear De-Clogging
**Applicable Equipment:** Fused Deposition Modeling (FDM) 3D Printers (Bowden & Direct Drive)  
**Disruption Level:** Non-Disruptive (Operator Level)  
**Safety Threshold:** Hotend operates at 200 C to 260 C. Avoid skin contact with nozzle or heater block.

1. **Atomic Cold Pull:**
   - Heat hotend to 220 C and feed 10cm of nylon or PLA filament manually into extruder.
   - Turn off heater and allow hotend to cool down to 90 C.
   - When temperature hits 90 C, firmly pull filament straight upward out of the hotend. The semi-molten filament will extract as a molded plug containing carbonized particles from the nozzle orifice.
2. **Acupuncture Needle Cleaning:** Heat hotend to 230 C. Insert a 0.35mm flexible acupuncture wire upward into the 0.40mm nozzle tip 4-5 times while extruding filament to clear micro-blockages.
3. **Extruder Tooth De-burring:** Open extruder tension idler arm. Inspect brass or hardened steel drive gear. Use a nylon brush to remove white/black filament shaving dust that causes teeth slippage.

### Procedure 3D-02: PEI Heated Bed Degreasing & 4-Corner Z-Offset Calibration
**Applicable Equipment:** Textured PEI Spring Steel Sheets & BLTouch / Inductive Bed Probes  
**Disruption Level:** Non-Disruptive (Operator Level)  
**Safety Threshold:** Heated bed surface operates at 60 C to 100 C.

1. **Dish Soap Degreasing:** Remove flexible spring steel PEI sheet. Wash under warm tap water with standard dish detergent (e.g. Dawn) using a soft sponge to remove invisible finger oils. Dry with clean paper towel and wipe with 99% Isopropyl Alcohol. Never touch the print area with bare fingers.
2. **Bed Thermal Soak:** Preheat bed to 60 C and allow 5 minutes for temperature to equalize across the aluminum plate before starting leveling routines.
3. **Corner Leveling:** Home all axes. Disable stepper motors. Slide a sheet of standard 80 GSM printer paper between nozzle and bed at each corner over adjustment thumbwheels. Adjust until paper slides with gentle dragging friction without buckling.
4. **Z-Offset Live Tuning:** Start a first-layer calibration print (five 20x20mm squares). Live tune Z-offset down by 0.02mm steps until extrusions form a flat ribbon with 50% squish and zero gaps between parallel tracks.

### Procedure 3D-03: Thermistor Retention & PID Loop Thermal Runaway Recovery
**Applicable Equipment:** NTC 100K 3950 Thermistors & 40W Heater Cartridges  
**Disruption Level:** Low-Disruption  
**Safety Threshold:** Disconnect power before adjusting heater block wiring to avoid shorting 24V into 3.3V MCU ADC pins.

1. **Thermistor Retention Screw Inspection:** Inspect small M3 retaining screw holding glass bead thermistor inside heater block. Screw must be snug enough to hold wires in place without biting into transparent fiberglass insulation sleeve.
2. **Silicone Sock Fitment:** Ensure high-temp silicone thermal sock covers the aluminum heater block completely. Stray airflow from 5015 part-cooling fan will trigger false Thermal Runaway alarms if block is uninsulated.
3. **PID Loop Auto-Calibration:** Send G-code command via USB terminal or LCD screen:
   `M303 E0 S210 C8` (runs 8 heating/cooling cycles at 210 C).
   Save resulting Kp, Ki, and Kd constants to EEPROM with `M500`.

---

## Residential Inverter & Home Battery Backup Troubleshooter

### Procedure INV-01: Battery Terminal De-Sulfation & Electrolyte Specific Gravity Top-Up
**Applicable Equipment:** 12V / 24V Deep-Cycle Tall Tubular Lead-Acid Battery Banks  
**Disruption Level:** Non-Disruptive (Operator Level)  
**Safety Threshold:** Battery cells produce explosive hydrogen gas during charging. Keep flames, sparks, and cigarettes away. Wear protective goggles.

1. **Terminal Corrosion Cleansing:** Inspect lead terminal lugs. If covered in powdery white/blue-green sulfate crystals:
   - Prepare solution of warm water and 2 tablespoons of baking soda.
   - Sponge onto terminals to neutralize sulfuric acid.
   - Scrub with wire brush until bright lead is exposed.
   - Coat thoroughly with pure petroleum jelly (Vaseline) to prevent air oxidation.
2. **Float Indicator Audit:** Inspect the 6 red/green float level indicators across battery top:
   - If red line sinks below green band, cell water is depleted.
   - Unscrew vent caps and add pure distilled water (never tap water or RO water) until green indicator rises.
3. **Hydrometer Specific Gravity Test:** Using a battery hydrometer, draw electrolyte from each cell:
   - Fully charged: 1.260 to 1.280 specific gravity.
   - 50% discharged: 1.200 specific gravity.
   - Fully discharged / dead cell: < 1.140 specific gravity.

### Procedure INV-02: Inrush Overload Shedding & Breaker Reset
**Applicable Equipment:** Pure Sine Wave Inverters (800VA to 3.5kVA)  
**Disruption Level:** Non-Disruptive (Operator Level)  
**Safety Threshold:** Do not touch exposed 230V AC output sockets with wet hands.

1. **High-Wattage Load Shedding:** Unplug all non-essential high-draw appliances from backup power sockets: space heaters, electric kettles, hair dryers, microwave ovens, and induction cooktops.
2. **Motor Surge Calculation:** Verify that inductive motor loads (refrigerators, washing machines) do not exceed inverter surge multiplier (typically 2x rated capacity for 500ms).
3. **Rear Circuit Breaker Reset:** Locate the black pushbutton circuit breaker labeled "OUTPUT OVERLOAD" on the inverter rear panel. Press firmly inward until it clicks to reset thermal trip mechanism.

### Procedure INV-03: Heat Sink Airflow & Cooling Fan Spool Verification
**Applicable Equipment:** Aluminum Extrusion Heat Sinks & 80mm/92mm DC Brushless Fans  
**Disruption Level:** Non-Disruptive (Operator Level)  
**Safety Threshold:** Keep fingers away from rotating fan blades.

1. **Chassis Clearance Audit:** Inverter requires minimum 20cm clearance on rear and side vents. Remove all cardboard boxes, clothing, or newspapers stored on top of or adjacent to the inverter cabinet.
2. **Intake Grille Vacuum:** Use vacuum cleaner brush attachment to remove dust blankets from the rear cooling fan intake grille.
3. **Fan Spool Diagnostic:** Apply heavy electrical load (e.g. 500W room lights) while running on battery power. Verify that internal cooling fan spins up smoothly without bearing screeching. If heatsink exceeds 80 C with fan stalled, thermal cutoff engages.

---

## Gaming Console Overheating & Disk Drive Diagnostic Guide

### Procedure GC-01: Radial Blower Fan De-Felting & Vacuum Catcher Clearing
**Applicable Equipment:** Current-Generation Gaming Consoles (Liquid Metal / Heatpipe Cooled)  
**Disruption Level:** Non-Disruptive (Operator Level)  
**Safety Threshold:** Unplug AC power cord and wait 20 minutes for APU heatsink to cool before handling.

1. **Outer Panel Pop-Off:** Place console horizontally on clean microfiber cloth. Gently lift the rear corner of top faceplate and slide toward bottom of console until locking hooks disengage.
2. **Vacuum Dust Catcher Depots:** Locate dedicated triangular dust catcher ports on the plastic inner housing. Place vacuum nozzle over holes to suck out dust bunnies accumulated in front of internal heatsink fin stacks.
3. **Fan Intake Blade Audit:** Inspect the 120mm radial intake fan blades with a flashlight. If blades are coated with greasy cigarette smoke or pet hair felting, gently hold fan blade with a plastic spudger (to prevent motor back-EMF) while wiping blades with a dry microfiber swab.
4. **Ventilation Orientation:** Ensure console has minimum 10cm open air clearance behind exhaust vents. Do not place console inside closed glass-door cabinets or on plush carpet rugs.

### Procedure GC-02: Blu-Ray Optical Pickup Lens Cleaning & Emergency Manual Eject
**Applicable Equipment:** Slot-Loading UHD Blu-ray Optical Disc Drives  
**Disruption Level:** Non-Disruptive to Low-Disruption  
**Safety Threshold:** Do not force stuck game discs out with pliers or tweezers.

1. **Disc Surface Inspection:** Inspect bottom data surface of non-reading game disc. Clean smudges by wiping with microfiber cloth in straight radial lines from center spindle hole outward to rim (never in circles).
2. **Drive Roller Cleaning:** If disc struggles to pull in or eject, wrap microfiber cloth dampened with isopropyl alcohol around clean cardboard strip and insert gently into drive slot mouth to clean rubber intake rollers.
3. **Emergency Manual Eject Screw:** If game disc is trapped inside unit:
   - Remove console bottom faceplate.
   - Locate the black circular rubber dust seal over the optical drive housing.
   - Peel seal back to reveal manual eject screw.
   - Turn clockwise with #1 Phillips screwdriver to manually rotate gear train and push out disc.

### Procedure GC-03: HDMI 2.1 Video Handshake Reset & Pin Integrity Inspection
**Applicable Equipment:** HDMI 2.1 FRL / TMDS 4K 120Hz Video Interfaces  
**Disruption Level:** Non-Disruptive (Operator Level)  
**Safety Threshold:** Turn off TV and console before hot-swapping HDMI cables to prevent static ESD damage to HDMI transmitter chip.

1. **Safe Mode Resolution Reset:**
   - With console in standby (amber light), press and hold power button.
   - Hold button down until you hear a second beep (approx. 7 seconds).
   - Release button; connect controller via USB cable.
   - In Safe Mode menu, choose "Change Video Output" -> "Change Resolution" -> select "1080p". This forces console to bypass broken 4K HDR EDID handshake.
2. **Cable Certification Verification:** Ensure cable is certified Ultra High Speed (48 Gbps) HDMI 2.1. Cheap non-certified HDMI cables drop video signal whenever 120Hz or VRR (Variable Refresh Rate) is requested by game engine.
3. **Physical Port Pin Inspection:** Use smartphone camera with flash zoomed 3x into console rear HDMI port. Verify that none of the 19 gold contact pins are pushed backward, bent upward, or touching adjacent pins.
