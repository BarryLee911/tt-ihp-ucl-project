# Mengrui's progect

UCL EEE summer project for Tiny Tapeout IHP, created from the [official IHP Verilog template](https://github.com/TinyTapeout/ttihp-verilog-template).

The design counts sign matches between an unsigned 8-bit ADC signal and a square-wave reference over a 1600-sample sliding window. It supports 23 frequency exponents and exposes an 11-bit count.

- [Interface, configuration, and hardware notes](docs/info.md)
- [Project configuration](info.yaml)
- [Simulation and implementation results](https://github.com/BarryLee911/tt-ihp-ucl-project/actions)

The top-level module is `tt_um_sine_area_detector`. The requested clock is 80 MHz; achievable timing and required tile area must be established by implementation results. Passing the repository checks does not place a fabrication order.
