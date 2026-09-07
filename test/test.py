"""Public-interface regression tests; no DUT internals are accessed.

These tests use the designer's stated startup and sampling contract. They run
functional stimulus at the 80 MHz target period; passing them does not establish
physical timing closure or external ADC interface timing.

Illegal exponent codes, the exact warm-up waveform, and large exponents are
deliberately outside these bounded checks because their contracts or practical
simulation durations have not been established.
"""

import math

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly, RisingEdge, Timer


CLOCK_PERIOD_NS = 12.5
WINDOW_SAMPLES = 1600
BALANCED_COUNT = WINDOW_SAMPLES // 2
WARMUP_CYCLES = 4000
SETTLED_CHECK_CYCLES = 256
TRANSITION_CYCLES = 1800


class Interface:
    """Drive inputs on falling edges and inspect only top-level output ports."""

    def __init__(self, dut):
        self.dut = dut
        dut.clk.value = 0
        dut.ena.value = 1
        dut.rst_n.value = 0
        dut.ui_in.value = 0
        dut.uio_in.value = 0
        self.clock_task = cocotb.start_soon(
            Clock(dut.clk, CLOCK_PERIOD_NS, unit="ns").start(start_high=False)
        )

    def result(self):
        """Read the 11-bit result and check pin direction and legal range."""
        values = []
        for name in ("uo_out", "uio_out", "uio_oe"):
            value = getattr(self.dut, name).value
            assert value.is_resolvable, f"{name} contains an unknown logic value"
            values.append(int(value))
        low, bidirectional, output_enable = values
        assert output_enable == 0xE0, (
            f"uio_oe must be 0xe0, got 0x{output_enable:02x}"
        )
        count = low | (((bidirectional >> 5) & 0x07) << 8)
        assert 0 <= count <= WINDOW_SAMPLES, (
            f"Public result outside 0..{WINDOW_SAMPLES}: {count}"
        )
        return count

    async def observe_edge(self):
        await RisingEdge(self.dut.clk)
        # Allow combinational output mapping to settle after sequential updates.
        await Timer(1, unit="ns")
        await ReadOnly()
        return self.result()

    async def reset(self, exponent, adc):
        assert 0 <= exponent <= 22
        await FallingEdge(self.dut.clk)
        self.dut.ena.value = 1
        self.dut.uio_in.value = exponent
        self.dut.ui_in.value = adc
        self.dut.rst_n.value = 0
        await ClockCycles(self.dut.clk, 10)
        await FallingEdge(self.dut.clk)
        self.dut.rst_n.value = 1
        # The designer specifies capture of N on this first rising edge.
        return await self.observe_edge()

    async def cycle(self, adc=None):
        await FallingEdge(self.dut.clk)
        if adc is not None:
            self.dut.ui_in.value = adc
        return await self.observe_edge()

    async def stable_window(self, exponent, adc):
        await self.reset(exponent, adc)
        for _ in range(WARMUP_CYCLES):
            await self.cycle()
        # At N=0 and N=1, 4000 clock cycles exceed a full 1600-sample
        # window even after allowing for the initial configuration edge.
        for cycle in range(SETTLED_CHECK_CYCLES):
            count = await self.cycle()
            assert count == BALANCED_COUNT, (
                f"N={exponent}, ADC={adc}, settled cycle={cycle}: "
                f"expected {BALANCED_COUNT}, got {count}"
            )


@cocotb.test()
async def full_windows_for_constant_input(dut):
    """Both signs give 800 matches with a complete balanced reference period."""
    interface = Interface(dut)
    for exponent in (0, 1):
        for adc in (0, 255):
            await interface.stable_window(exponent, adc)


async def threshold_trace(interface, low_adc, high_adc):
    """Capture reproducible sign changes without assuming reference phase."""
    await interface.reset(0, low_adc)
    for _ in range(WARMUP_CYCLES):
        await interface.cycle()
    assert interface.result() == BALANCED_COUNT

    trace = []
    for adc in (high_adc, low_adc):
        previous = interface.result()
        segment = []
        for cycle in range(TRANSITION_CYCLES):
            count = await interface.cycle(adc if cycle == 0 else None)
            assert abs(count - previous) <= 1, (
                f"Sliding-window count changed by more than one sample: "
                f"{previous} -> {count}"
            )
            previous = count
            segment.append(count)

        # Replacing a complete constant-sign window by its opposite changes
        # the count in opposite directions during the reference's two equal
        # half-periods. For any starting phase the excursion is at least 400;
        # allow one sample for the edge at which the new input is first used.
        excursion = max(abs(count - BALANCED_COUNT) for count in segment)
        assert excursion >= 399, (
            f"Sign reversal produced insufficient response: excursion={excursion}"
        )
        assert all(count == BALANCED_COUNT for count in segment[-128:]), (
            "The count did not return to 800 after a complete new window"
        )
        trace.extend(segment)
    return trace


@cocotb.test()
async def unsigned_threshold_and_dynamic_response(dut):
    """Verify the 127/128 boundary and a nonconstant moving-window response."""
    interface = Interface(dut)
    extremes = await threshold_trace(interface, low_adc=0, high_adc=255)
    boundary = await threshold_trace(interface, low_adc=127, high_adc=128)

    assert len(extremes) == len(boundary) == 2 * TRANSITION_CYCLES
    for cycle, (extreme_count, boundary_count) in enumerate(zip(extremes, boundary)):
        assert extreme_count == boundary_count, (
            f"Threshold-equivalent inputs differed at cycle {cycle}: "
            f"0/255 trace={extreme_count}, 127/128 trace={boundary_count}"
        )


async def periodic_sine_count(interface, exponent, complement):
    """Use the supplied testbenches' sine stimulus with the stated startup."""
    period_cycles = WINDOW_SAMPLES * (1 << exponent)
    phase = math.radians(37.5)
    codes = [
        min(255, max(0, math.floor(
            128 + 127 * math.sin(2 * math.pi * cycle / period_cycles + phase) + 0.5
        )))
        for cycle in range(period_cycles)
    ]
    if complement:
        # For an unsigned threshold at 128, this inverts every input sign,
        # including the quantized samples on either side of the threshold.
        codes = [255 - code for code in codes]

    await interface.reset(exponent, codes[0])
    # Four real periods allow all history and ordinary output latency to settle.
    # Unlike the older supplied testbenches, this never forces sample_tick.
    for cycle in range(4 * period_cycles):
        await interface.cycle(codes[cycle % period_cycles])

    counts = []
    for code in codes:
        counts.append(await interface.cycle(code))

    assert min(counts) == max(counts), (
        f"N={exponent}, complement={complement}: a settled periodic input "
        f"did not give a constant full-window count ({min(counts)}..{max(counts)})"
    )
    return counts[0]


@cocotb.test()
async def periodic_sine_and_complement(dut):
    """A waveform and its inverse must partition all 1600 reference matches."""
    interface = Interface(dut)
    for exponent in (0, 1):
        normal = await periodic_sine_count(interface, exponent, complement=False)
        inverse = await periodic_sine_count(interface, exponent, complement=True)
        # Reset reference phase need not be known: identical startup makes the
        # two runs comparable, and each sample matches exactly one of the signs.
        assert normal + inverse == WINDOW_SAMPLES, (
            f"N={exponent}: sine and complement counts must sum to "
            f"{WINDOW_SAMPLES}, got {normal} + {inverse}"
        )
