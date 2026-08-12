///////////////////////////////////////////////////////////////////////
// counter
//
// Purpose: Synchronous up counter used as the second cocotb tutorial
//          example: clock, synchronous active-high reset, count
//          enable, and a Wrap flag that pulses in the cycle the
//          counter rolls over from MAX to 0.
// Author:  Ratko Pilipovic
// Date:    11 August 2026
///////////////////////////////////////////////////////////////////////

module counter #(parameter WIDTH = 4) (
  input  logic             clk, reset, en,
  output logic [WIDTH-1:0] Count,
  output logic             Wrap);

  localparam logic [WIDTH-1:0] MAX = {WIDTH{1'b1}};

  always_ff @(posedge clk)
    if (reset) Count <= '0;
    else if (en) Count <= Count + 1'b1;

  // combinational: high during the cycle that will wrap the counter
  assign Wrap = en & (Count == MAX);

endmodule
