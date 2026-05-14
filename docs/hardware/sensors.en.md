# Sensors

## PCAN-GPS FD (PEAK System)

The PCAN-GPS FD module provides IMU and GPS data via the CAN bus, published as ROS2 topics.

| Spec | Value |
|------|-------|
| Microcontroller | NXP LPC4000 series (ARM Cortex-M4) |
| GNSS receiver | u-blox MAX-7W (GPS, GLONASS, QZSS, SBAS) |
| Accelerometer + Magnetometer | Bosch BMC050 (3-axis each) |
| Gyroscope | STMicroelectronics L3GD20 (3-axis) |
| CAN | High-speed CAN (ISO 11898-2), 40 kbit/s to 1 Mbit/s |
| CAN protocol | CAN 2.0 A/B |
| Digital inputs | 2 (high-active) |
| Digital output | 1 (low-side driver) |
| Connector | 10-pin Phoenix terminal block |
| Power | 8–30 V DC |
| Storage | microSD slot (data logging) |
| Operating temperature | -40 to +85 °C |

**Test results:**

- **IMU:** Raw data access successful via CAN bus and ROS2 topics
- **GPS:** Coordinates not obtained during tests — tests were performed indoors without satellite signal

## Lucid Vision TRI032S-CC

| Spec | Value |
|------|-------|
| Model | LUCID Triton TRI032S-CC |
| Serial | 243901923 |
| Sensor | Sony IMX265 CMOS (Global Shutter) |
| Resolution | 3.2 MP (2048 × 1536 px) |
| Frame rate | ~35.4 FPS (base) |
| Interface | GigE Vision (1000BASE-T via M12 connector) |
| Sensor size | 8.9 mm (1/1.8" type) |
| Pixel size | 3.45 µm |
| Lens mount | C-Mount |
| Protection | IP67 (dust and water resistant) |
| Power | PoE (Power over Ethernet) or 12–24 VDC external |

**Operational status:**
- Feed running at ~30 FPS, visible on vehicle's onboard display
- Multi-camera initialization bug (camera ID conflict) — fixed
- Streaming via NetBird VPN: stable; topics accessible; rqt non-functional over VPN (use Python viewer script instead)

!!! note "Lens"
    The TRI032S-CC ships without a lens. A C-mount lens must be installed. A missing lens was identified and corrected during initial setup.

See [Camera Overview](../camera/index.md) for driver and configuration details.

## On-board PC

- OS: Ubuntu 22.04 LTS
- ROS2 Humble packages successfully launched
- Topic visualization confirmed in ROS2
