///////////////////////////////////////////////////////////////////////
// mux3
//
// Purpose: Parameterized 3-to-1 multiplexer.
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module mux3 #(parameter WIDTH = 8) (
  input  logic [WIDTH-1:0] D0, D1, D2,
  input  logic [1:0]       S,
  output logic [WIDTH-1:0] Y);

  // 3-to-1 multiplexer, 2-bit select
  //   S = 00 -> Y = D0
  //   S = 01 -> Y = D1
  //   S = 10 -> Y = D2
  //   S = 11 -> Y = D0 (fallback)
  //   - nested conditional operator: test S == 2'b10 first, then S == 2'b01
  assign Y = (S == 2'b10) ? D2 : ((S == 2'b01) ? D1 : D0);
endmodule
