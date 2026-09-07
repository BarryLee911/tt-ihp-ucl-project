## How it works

This project measures sign agreement between an unsigned 8-bit ADC input and an internal square-wave reference. ADC values below 128 represent logic 0; values at or above 128 represent logic 1. The output counts matching samples in the most recent 1600-sample window, with a range of 0 to 1600.

The frequency exponent `N` selects one sample every `2^N` clock cycles. One reference period contains 1600 samples, so:

`reference_frequency_hz = clock_frequency_hz / (1600 * 2^N)`

Legal exponents are 0 through 22. At the 80 MHz design target, exponent 0 gives 50 kHz and exponent 22 gives approximately 0.01192093 Hz. Actual operating frequency depends on the supplied clock and the implementation timing results.

| Signal | Function |
| --- | --- |
| `ui_in[7:0]` | Unsigned 8-bit ADC sample. |
| `uo_out[7:0]` | Overlap count bits 7 through 0. |
| `uio_in[4:0]` | Frequency exponent, 0 through 22. |
| `uio_out[7:5]` | Overlap count bits 10 through 8. |
| `uio_oe[7:0]` | `11100000`: upper three pins are outputs, lower five are inputs. |
| `clk` | External clock; target 80 MHz. |
| `rst_n` | Active-low reset. |
| `ena` | Tiny Tapeout project-selection enable. |

Reconstruct the result as `{uio_out[7:5], uo_out[7:0]}`. A count of 1600 represents agreement at every sample; 0 represents disagreement at every sample. A constant input sign produces 800 after a complete balanced reference window.

## How to test

1. Select the project and keep `ena = 1` throughout configuration and operation.
2. Set `uio_in[4:0]` to the desired exponent, assert `rst_n = 0` while supplying the clock, then release reset.
3. Keep the exponent stable through the first rising clock edge after reset release, when it is latched. To change the active exponent, repeat the reset sequence with the new value.
4. Apply ADC data with timing appropriate to the input clock. Allow at least one full 1600-sample window to accumulate after configuration before interpreting the steady-state count. No separate result-valid pin is provided.
5. Read the upper three and lower eight result bits coherently. Do not drive bidirectional pins 5 through 7 externally.

The repository's cocotb tests exercise the external interface using the selected-project reset sequence. GitHub Actions runs functional simulation and the IHP implementation workflow. The workflow results, rather than this document, indicate which checks have passed for a particular commit.

For manual checks, hold the ADC value at 0 or 255 and verify a completed-window result of 800. Apply a periodic ADC input at the selected reference frequency and vary its phase to observe changes in the overlap count. Values 127 and 128 exercise the sign threshold. Exponent codes 23 through 31 are outside the supported operating range.

## External hardware

Provide an external clock, active-low reset, five exponent inputs, and an unsigned 8-bit digital ADC signal or digital test pattern. Read the 11-bit result using the pin mapping above. Select an ADC and clock arrangement with compatible voltage levels and adequate setup and hold timing for the chosen Tiny Tapeout board. If the ADC uses a separate clock, arrange for complete input samples to be transferred reliably.

The 80 MHz clock is a design target. Hardware operation at that frequency requires satisfactory implementation timing and external interface timing; it is not established by an RTL simulation alone.
