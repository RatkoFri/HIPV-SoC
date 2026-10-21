///////////////////////////////////////////////////////////////////////
// alu
//
// Purpose: Arithmetic-logic unit for the HIPV core. Implements the
//          ten RV32I integer operations selected by ALUControl
//          (encoding in hipv_pkg). Shift amount is B[4:0].
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module alu (input  logic [31:0] A, B,
            input  logic [3:0]  ALUControl,
            output logic [31:0] Y);

  // 0. import hipv_pkg::* for the ALU_* encodings

  // 1. always_comb case (ALUControl)
  //      ALU_ADD:  A + B
  //      ALU_SUB:  A - B
  //      ALU_SLL:  A << B[4:0]          (shift amount is only 5 bits)
  //      ALU_SLT:  signed A < B   -> {31'b0, result}   (use $signed)
  //      ALU_SLTU: unsigned A < B -> {31'b0, result}
  //      ALU_XOR:  A ^ B
  //      ALU_SRL:  A >> B[4:0]
  //      ALU_SRA:  $signed(A) >>> B[4:0], cast back with $unsigned
  //      ALU_OR:   A | B
  //      ALU_AND:  A & B
  //      default:  32'b0

endmodule
