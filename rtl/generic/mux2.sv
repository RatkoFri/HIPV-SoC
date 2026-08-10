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

  assign Y = S ? D1 : D0;

endmodule
