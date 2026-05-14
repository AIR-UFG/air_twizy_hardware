# Status & Roadmap

## What's working

### Hardware

| Component | Status |
|-----------|--------|
| Renault Twizy 80 (vehicle) | Operational — service light ON, maintenance pending |
| Auxiliary battery (12V Varley) | Functional — replacement recommended |
| Traction battery | Unknown state — OBD2/CAN diagnostic needed |
| StreetDrone XCU | Operational on `can2` |
| PCAN-GPS FD | IMU working via CAN; GPS untested outdoors |
| Lucid Vision TRI032S-CC | ~30 FPS feed confirmed; C-mount lens installed |
| Ouster LiDAR | Driver operational; network config via dnsmasq documented |
| Teltonika RUT950 | Validated with test SIM; production SIM needed |

### Software

| Component | Status |
|-----------|--------|
| ROS2 Humble + Docker stack | Running on vehicle PC |
| FastDDS Discovery Server | Operational on `twizy:11811` |
| NetBird VPN | Mesh P2P confirmed; hostname `twizy` resolves |
| CAN interface (`can2`) | Frames received, XCU control confirmed |
| Xbox teleop (`direct_control`) | Working end-to-end over VPN |
| Camera driver (arena_camera_ros2) | ~30 FPS, streaming over VPN stable |
| LiDAR driver (ouster_ros) | Driver launches; point cloud published |
| Gazebo simulation | Loads; keyboard teleop works |
| GitHub Pages docs | Deployed at [air-ufg.github.io/air_twizy_hardware](https://air-ufg.github.io/air_twizy_hardware) |

---

## Known issues

| Issue | Severity | Notes |
|-------|----------|-------|
| Service light ON | Medium | Electronic/mechanical inspection required before extended use |
| Auxiliary battery aging | Medium | >4 years old; deep discharge history; custom bracket needed for replacement |
| GPS untested outdoors | Low | PCAN-GPS FD IMU works; coordinates were never validated with satellite signal |
| `rqt` non-functional over VPN | Low | Use Python viewer script as workaround |
| Lab outlet grounding | High | 20A rated outlet with correct earth ground required for charging |
| RUT950 SIM card | Medium | Test SIM only — no production connectivity plan |
| `can0` / `can1` unusable | Known | XCU is hardwired to `can2`; this is expected behavior, not a bug |

---

## Roadmap

### Short term

- [ ] Replace auxiliary battery and fabricate mounting bracket
- [ ] Purchase production SIM plan for RUT950
- [ ] Perform OBD2 diagnostic to assess traction battery health
- [ ] Test GPS outdoors and validate PCAN-GPS FD coordinates
- [ ] Inspect service light fault codes

### Medium term

- [ ] Document multi-camera setup (second Lucid Vision unit)
- [ ] Validate LiDAR + camera spatial calibration (extrinsic)
- [ ] Add IMU data integration to the ROS2 nav stack
- [ ] Test teleoperation latency over 4G (not just WiFi/LAN)
- [ ] Replace lab charging outlet with 20A grounded outlet

### Long term

- [ ] Integrate LiDAR + camera into a perception pipeline
- [ ] Implement autonomous braking / obstacle avoidance
- [ ] Add remote monitoring dashboard (vehicle state, battery, GPS track)
- [ ] Outdoor autonomous navigation test
- [ ] Document StreetDrone XCU firmware version and update procedure
