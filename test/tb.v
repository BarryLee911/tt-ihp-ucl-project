`default_nettype none
`timescale 1ns / 1ps

// Interface wrapper adapted from the official Tiny Tapeout IHP template.
module tb ();
  // Record only the public testbench signals, not the DUT's internal state.
  initial begin
    $dumpfile("tb.fst");
    $dumpvars(1, tb);
    #1;
  end

  reg clk;
  reg rst_n;
  reg ena;
  reg [7:0] ui_in;
  reg [7:0] uio_in;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;

  tt_um_sine_area_detector user_project (
`ifdef USE_POWER_PINS
      .VDPWR  (1'b1),
      .VGND   (1'b0),
`endif
      .ui_in  (ui_in),
      .uo_out (uo_out),
      .uio_in (uio_in),
      .uio_out(uio_out),
      .uio_oe (uio_oe),
      .ena    (ena),
      .clk    (clk),
      .rst_n  (rst_n)
  );
endmodule

`default_nettype wire
