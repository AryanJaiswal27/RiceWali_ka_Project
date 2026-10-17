# Enterprise Network Gateway Industrial Service Manual

## Document Information
- Document ID: ESM-NET-2026-V4
- Classification: Corporate IT Infrastructure & Field Engineering Standard
- Target Devices: Apex Router Pro-X (Model ID: ARPX-800) and CoreSwitch 4000 (Model ID: CS4K-48T)
- Compliance Standard: IEEE 802.3, IEC 62368-1, Telcordia GR-63-CORE NEBS Level 3

---

## 1. Safety Directives & Technician Authorization Boundaries

### 1.1 Field Authorization Levels
- **Tier 1 (Site Operator / L1 Support):** Permitted to execute read-only CLI telemetry queries, inspect external status LEDs, verify AC power cord seating, and clean external optical fiber patch cords using dry-cassette lint-free tools.
- **Tier 2 (Systems Administrator / L2 Support):** Permitted to alter software QoS profiles, renegotiate BGP sessions, update firmware images signed by enterprise root CA, and reconfigure port priorities.
- **Tier 3 (Certified Field Technician / L3 Hardware Engineer):** Mandatory for any invasive chassis procedures:
  - Opening outer metal chassis enclosures or top covers.
  - Hot-swapping modular fan trays when active cooling interlocks are engaged.
  - Replacing SFP+/SFP28 optical transceivers inside energized dense cages.
  - Line card extraction, backplane trace inspection, or torque-calibrated reseating.
  - Flash memory, JTAG diagnostics, or Cryptographic Hardware Security Module (HSM) servicing.

### 1.2 Mandatory Hazard Warnings
- **Optical Radiation Hazard:** Class 1M and Class 3R laser emissions are present on active optical ports (1310nm / 1550nm). Never stare into bare fiber connectors or optical transceiver bores with magnifying instruments. Always install dust caps when fibers are disconnected.
- **High Voltage & Stored Energy:** Chassis PSUs maintain hazardous DC voltage levels (400V internal bus) for up to 300 seconds post AC disconnection. Do not probe unshielded PSU pins.
- **Electrostatic Discharge (ESD):** A calibrated ESD wrist strap bonded to the chassis grounding lug is required before touching any line card, SFP cage, or internal trace. Minimum threshold: 1 Megohm series resistor.

---

## 2. Apex Router Pro-X (Model ID: ARPX-800)

### 2.1 Hardware Specifications
- **Processing Architecture:** Dual 16-Core Enterprise Carrier CPU @ 2.8 GHz, 64 GB ECC DDR5 memory.
- **Storage Subsystem:** Dual 256 GB NVMe SSD (RAID-1 Boot Array) + 8 MB SPI Flash (Secure Boot & Safe-Recovery).
- **Interface Matrix:** 4x 100GbE QSFP28 Uplink Ports, 16x 25GbE SFP28 WAN/LAN Ports, 2x 10GbE RJ45 Management Ports.
- **Thermal Rating:** Operating ambient: 0 C to 45 C (32 F to 113 F). Storage ambient: -40 C to 70 C.
- **Power Rating:** Dual Hot-Swap 800W 80-PLUS Titanium PSUs (100-240 VAC, 50-60 Hz / 240 VDC).

### 2.2 Subsystem Diagnostic Procedures: Apex Router Pro-X

#### Procedure ARPX-PROC-01: Optical Transceiver & WAN Signal Degradation
- **Target Subsystem:** SFP28 WAN Interface & Transceiver Cage
- **Associated Error Codes:** ERR-ARPX-101
- **Sequential Diagnostic Steps:**
  1. **Step 1 (Least Disruptive - Software Telemetry):**
     Execute CLI command `show interfaces wan0 optical-diagnostics`. Inspect Tx Power (nominal: -1.0 to -7.0 dBm) and Rx Power (acceptable: -2.0 to -20.0 dBm). If Rx Power is lower than -24.0 dBm, signal attenuation or fiber break is verified.
  2. **Step 2 (Physical Cable Inspection):**
     Inspect patch cable bend radius (minimum 30 mm). Verify that the LC duplex connector click-lock mechanism is completely seated.
  3. **Step 3 (Polarity & Continuity Check):**
     Verify TX/RX polarity swap at patch panel. Use an optical power meter (OPM) calibrated at 1310 nm on the incoming fiber lead to verify signal presence from the upstream service provider.
  4. **Step 4 (Connector Cleaning):**
     Clean fiber ferrule using an approved one-click dry cleaner. Reconnect and re-read optical diagnostics.
  5. **Step 5 [CRITICAL TECHNICIAN BOUNDARY - HALT]:**
     If optical Rx remains below -24.0 dBm after cleaning, transceiver hardware failure is confirmed. Transceiver extraction and replacement inside the live chassis requires an Authorized Field Technician. Do not force transceiver unlatch bail.

#### Procedure ARPX-PROC-02: Control Plane BGP Peering Instability
- **Target Subsystem:** Routing Engine & Routing Information Base (RIB)
- **Associated Error Codes:** ERR-ARPX-204
- **Sequential Diagnostic Steps:**
  1. **Step 1 (Session State Telemetry):**
     Execute `show ip bgp summary` and inspect 'Prefixes Received' and 'Last Reset Reason'. If reset reason indicates 'Hold Timer Expired', check keepalive/holdtime intervals (standard: 30s/90s).
  2. **Step 2 (Resource Audit):**
     Execute `show system resources` and check Memory Buffer utilization on Control Core 0. If utilization exceeds 92%, verify route filtering rules.
  3. **Step 3 (Interface MTU Harmonization):**
     Execute `show interfaces wan0 mtu` to ensure MTU matches the peer link configuration (default 1500; Jumbo 9000). Mismatched MTU causes silent dropping of large BGP UPDATE packets during route convergence.
  4. **Step 4 (Soft Reset Peering):**
     Issue non-disruptive soft reset: `clear ip bgp <neighbor_ip> soft in`. Confirm route table stabilizes.
  5. **Step 5 [ESCALATION]:**
     If route table flutters persist and memory leaks are indicated in system kernel log (`dmesg | grep oom`), record core dump and escalate to Tier-3 Network Engineering for OS patch application.

#### Procedure ARPX-PROC-03: Chassis Thermal & Airflow Management
- **Target Subsystem:** Cooling Fan Assembly & Thermal Sensors
- **Associated Error Codes:** ERR-ARPX-310
- **Sequential Diagnostic Steps:**
  1. **Step 1 (Thermal Zone Mapping):**
     Execute `show system environment thermal`. Note temperatures across Zone 1 (ASIC), Zone 2 (Control Plane), Zone 3 (Power Supply Inlet), and Zone 4 (Exhaust). Operating limit is 85 C.
  2. **Step 2 (Rack Environmental Assessment):**
     Measure rack cold-aisle ambient temperature. Confirm ambient is below 25 C and perforated rack door is not obstructed by blanking panels or cable bundles.
  3. **Step 3 (Fan PWM Telemetry):**
     Execute `show system environment fans`. Check RPM for Fan Units 1 through 4. Standard operating velocity: 7200 RPM. If any fan reports <3000 RPM or 'STALLED', proceed to step 4.
  4. **Step 4 [CRITICAL TECHNICIAN BOUNDARY - HALT]:**
     Internal chassis fan blower module replacement requires Authorized Field Technician intervention. Chassis top panel interlock switch triggers system shutdown if opened by unauthorized staff.

#### Procedure ARPX-PROC-04: Non-Volatile Memory Integrity & Recovery
- **Target Subsystem:** Secure SPI Flash & NVRAM Storage
- **Associated Error Codes:** ERR-ARPX-402
- **Sequential Diagnostic Steps:**
  1. **Step 1 [MANDATORY IMMEDIATE HALT - AUTHORIZED TECHNICIAN ONLY]:**
     NVRAM checksum errors indicate hardware bit rot or flash write endurance exhaustion.
  2. **Safety Directive:**
     Do NOT execute chassis power-cycle or restart. Doing so causes bootloader initialization failure.
  3. **Operator Action:**
     Connect auxiliary out-of-band management console cable, export diagnostic log via `show log system > tftp://audit-server/arpx_nvram.log`, and immediately dispatch an Authorized Field Technician equipped with the hardware flash module replacement kit (FRU-ARPX-NVRAM-402).

---

## 3. CoreSwitch 4000 (Model ID: CS4K-48T)

### 3.1 Hardware Specifications
- **Processing Architecture:** Multi-threaded Network Switching ASIC with 12.8 Tbps full-duplex switching capacity.
- **Port Density:** 48x 10/25GbE SFP28 Tri-Speed ports, 8x 100GbE QSFP28 Uplink Ports, dedicated Out-of-Band (OOB) Ethernet.
- **Packet Buffer:** 64 MB Integrated Ultra-Fast Dynamic Shared Memory Pool.
- **PoE Capability:** Integrated PoE+ Controller delivering up to 1440W total chassis budget (Class 4 / Class 6 compliant).
- **Physical Form Factor:** 2RU Modular Chassis with 3 Redundant Fan Trays and 2 Hot-Swap 1600W Power Supplies.

### 3.2 Subsystem Diagnostic Procedures: CoreSwitch 4000

#### Procedure CS4K-PROC-01: Packet Buffer Allocation & ECN Congestion
- **Target Subsystem:** Switch Fabric Dynamic Buffer Engine
- **Associated Error Codes:** ERR-CS4K-108
- **Sequential Diagnostic Steps:**
  1. **Step 1 (Ingress Drop Telemetry):**
     Run `show interfaces priority-queue counters` to identify which queues are accumulating tail drops. High drop rates on CoS 5 (Voice/Video) or CoS 3 (Storage iSCSI) signify traffic bursts exceeding burst absorption capability.
  2. **Step 2 (Buffer Threshold Verification):**
     Execute `show qos buffer-allocation profile`. Ensure buffer sharing mode is set to 'DYNAMIC_BURST' rather than 'STATIC_ALLOCATION'.
  3. **Step 3 (Flow Control Audit):**
     Check link-level flow control using `show interfaces flowcontrol status`. Verify Priority Flow Control (PFC) pause frames are negotiated with downstream hypervisors.
  4. **Step 4 (Remediation via Configuration):**
     Apply dynamic microburst buffer profile: `configure terminal; qos profile ultra-burst apply; commit`. Observe packet drops for 120 seconds.

#### Procedure CS4K-PROC-02: Chassis Backplane Interconnect Bus Integrity
- **Target Subsystem:** High-Speed SerDes Backplane Interconnect
- **Associated Error Codes:** ERR-CS4K-215
- **Sequential Diagnostic Steps:**
  1. **Step 1 (Hardware Bus Error Telemetry):**
     Execute `show fabric backplane errors linecard 2`. Record total Bit Error Rate (BER) and Cyclic Redundancy Check (CRC) error accumulations across lanes 0 through 15.
  2. **Step 2 (Software Traffic Re-routing):**
     Administratively shift ingress traffic to Line Card 1: `config linecard 2 standby enable`. This isolates user traffic from corrupted backplane transmissions.
  3. **Step 3 [CRITICAL TECHNICIAN BOUNDARY - HALT]:**
     Never attempt to pull, reseat, or tighten line card retention screws while the system is energized without an Authorized Field Technician. Backplane pins are gold-plated differential pairs susceptible to pin bending and catastrophic multi-card short circuits. Certified technician must inspect with 10x optical loupe and torque wrench to exactly 6.2 in-lbs.

#### Procedure CS4K-PROC-03: PoE+ Subsystem Overdraft & Distribution
- **Target Subsystem:** Power-over-Ethernet Controller & Voltage Regulators
- **Associated Error Codes:** ERR-CS4K-330
- **Sequential Diagnostic Steps:**
  1. **Step 1 (Inline Power Audit):**
     Execute `show power inline linecard 3`. Check 'Total Allocated Power' versus 'Total Reserve Power'. If allocated power reaches >740W on a single 740W power plane, low-priority ports are automatically shed.
  2. **Step 2 (Device Classification Audit):**
     Identify devices consuming IEEE 802.3at Class 4 (30.0W) or Class 6 (60.0W). Cross-reference MAC addresses with site asset database.
  3. **Step 3 (Port Priority Provisioning):**
     Configure non-essential endpoints (e.g., meeting room digital displays) to Priority Low: `interface range gigabitethernet 3/0/24-48; power inline priority low; commit`.
  4. **Step 4 (Cable Resistance Validation):**
     Run Time Domain Reflectometry (TDR) test on overloaded lines: `test cable-diagnostics tdr interface gigabitethernet 3/0/12`. Ensure loop resistance is under 12.5 ohms. Higher resistance causes excessive I^2*R voltage loss, triggering controller overdraft alarms.

#### Procedure CS4K-PROC-04: Modular Fan Tray Interlock & Replacement
- **Target Subsystem:** N+1 Redundant Modular Fan Tray Assembly
- **Associated Error Codes:** ERR-CS4K-412
- **Sequential Diagnostic Steps:**
  1. **Step 1 (Tachometer Status):**
     Run `show environment fan`. Identify the exact fan tray unit (Unit 1, 2, or 3) and sub-rotor index showing RPM = 0.
  2. **Step 2 (Thermal Headroom Calculation):**
     Verify that adjacent fan trays have automatically ramped up to emergency 100% velocity (12,000 RPM). Confirm chassis internal ASIC temperatures do not exceed 78 C.
  3. **Step 3 [CRITICAL TECHNICIAN BOUNDARY - HALT]:**
     Replacing a defective modular fan tray in the CoreSwitch 4000 requires an Authorized Field Technician.
     **Strict Safety Rule:** The chassis hot-swap thermal interlock permits an extraction window of AT MOST 180 SECONDS before thermal runaway forces an emergency hard shutdown. Only authorized personnel with the replacement module unboxed and pre-aligned are permitted to proceed.

#### Procedure CS4K-PROC-05: Cryptographic Hardware Security Module Tamper Lockout
- **Target Subsystem:** Secure Enclave & Zeroization Relays
- **Associated Error Codes:** ERR-CS4K-520
- **Sequential Diagnostic Steps:**
  1. **Step 1 [MANDATORY IMMEDIATE HALT - AUTHORIZED TECHNICIAN ONLY]:**
     The cryptographic tamper alert signifies physical enclosure breach detection, micro-switch trigger, or severe voltage transient on the secure coprocessor.
  2. **Safety Directive:**
     Do not reboot or attempt factory password reset. The crypto-keys have been safely zeroized.
  3. **Operator Action:**
     Secure physical access to rack cage. Document chassis serial number, rack cage access logs, and dispatch Authorized Security Hardware Engineer with cryptographic provisioning smartcard.

---

## 4. Master Diagnostic Verification Matrix
| Subsystem | Diagnostic Metric | Normal Baseline | Fault Threshold | Authorized Technician Required |
| :--- | :--- | :--- | :--- | :--- |
| SFP28 WAN Optical | Rx Optical Power | -2.0 to -14.0 dBm | < -24.0 dBm | NO (L1 cleaning) / YES (Optic replacement) |
| BGP Routing Engine | Control CPU Load | < 35% | > 85% sustained | NO |
| Chassis Thermal | ASIC Junction Temp | 42 C - 68 C | > 85 C | YES (Fan/Heatsink hardware replacement) |
| NVRAM / Boot Storage| Checksum Audit | 0 mismatches | >= 1 mismatch | YES (MANDATORY HALT) |
| Switch Buffer Fabric | Tail Drop Counters | 0 drops/sec | > 500 drops/sec | NO |
| High-Speed Backplane | SerDes CRC Errors | 0 errors/hr | > 10^-5 BER | YES (MANDATORY HALT) |
| PoE+ Power Subsystem | Line Card Wattage | < 80% capacity | > 100% capacity | NO |
| Redundant Fan Tray | Tachometer Feedback| > 6000 RPM | 0 RPM (Lock) | YES (MANDATORY HALT) |
| Crypto Security Module| Enclave Integrity | Intact (Status 0)| Tamper (Status 1)| YES (MANDATORY HALT) |
