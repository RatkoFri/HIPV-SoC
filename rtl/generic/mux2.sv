///////////////////////////////////////////////////////////////////////
// mux2
//
// Purpose: Parameterized 2-to-1 multiplexer.
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module mux2 #(parameter WIDTH = 8) (
  input  logic [WIDTH-1:0] D0, D1,
  input  logic             S,
  output logic [WIDTH-1:0] Y);

  // 2-to-1 multiplexer
  //   S = 0 -> Y = D0
  //   S = 1 -> Y = D1
  //   - one continuous assignment with the conditional operator ( ? : )
  assign Y = S ? D1 : D0;
endmodule
