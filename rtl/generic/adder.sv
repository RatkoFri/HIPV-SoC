///////////////////////////////////////////////////////////////////////
// adder
//
// Purpose: Parameterized adder.
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module adder #(parameter WIDTH = 8) (
  input  logic [WIDTH-1:0] A, B,
  output logic [WIDTH-1:0] Y);

  assign Y = A + B;

endmodule
