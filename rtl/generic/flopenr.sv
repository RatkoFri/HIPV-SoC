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

  always_ff @(posedge clk)
    if (reset) Q <= '0;
    else if (en) Q <= D;

endmodule
