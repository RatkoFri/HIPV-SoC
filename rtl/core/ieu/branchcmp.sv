///////////////////////////////////////////////////////////////////////
// branchcmp
//
// Purpose: Branch comparator. Evaluates the RV32I branch condition
//          selected by funct3 on the (forwarded) register operands,
//          independently of the ALU.
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module branchcmp (input  logic [31:0] A, B,
                  input  logic [2:0]  Funct3E,
                  output logic        TakenE);

  // 1. always_comb case (Funct3E)
  //      000 beq:  A == B
  //      001 bne:  A != B
  //      100 blt:  signed   A <  B   ($signed)
  //      101 bge:  signed   A >= B
  //      110 bltu: unsigned A <  B
  //      111 bgeu: unsigned A >= B
  //      default (010, 011 reserved): 0

endmodule
