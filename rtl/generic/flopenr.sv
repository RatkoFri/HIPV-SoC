///////////////////////////////////////////////////////////////////////
// flopenr
//
// Purpose: Parameterized flip-flop with synchronous reset and enable.
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module flopenr #(parameter WIDTH = 8) (
  input  logic             clk, reset, en,
  input  logic [WIDTH-1:0] D,
  output logic [WIDTH-1:0] Q);

  // Register with synchronous reset and enable
  //   - always_ff on the rising edge of clk
  //   - reset (active-high, synchronous): Q <= all zeros ('0)
  //   - else if en:                       Q <= D
  //   - otherwise Q keeps its value (no else branch needed)

endmodule
