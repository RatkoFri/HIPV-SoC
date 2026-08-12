///////////////////////////////////////////////////////////////////////
// tiny_alu
//
// Purpose: Small purely combinational ALU used as the first cocotb
//          tutorial example. No clock, no reset: outputs follow the
//          inputs after a delta cycle.
//            Op 00 = add, 01 = sub, 10 = and, 11 = or
//          Zero is high when Y is zero.
// Author:  Ratko Pilipovic
// Date:    11 August 2026
///////////////////////////////////////////////////////////////////////

module tiny_alu #(parameter WIDTH = 8) (
  input  logic [WIDTH-1:0] A, B,
  input  logic [1:0]       Op,
  output logic [WIDTH-1:0] Y,
  output logic             Zero);

  always_comb
    case (Op)
      2'b00:   Y = A + B;
      2'b01:   Y = A - B;
      2'b10:   Y = A & B;
      default: Y = A | B;
    endcase

  assign Zero = (Y == '0);

endmodule
