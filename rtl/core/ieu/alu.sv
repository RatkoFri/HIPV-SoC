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

  import hipv_pkg::*;

  always_comb
    case (ALUControl)
      ALU_ADD:  Y = A + B;
      ALU_SUB:  Y = A - B;
      ALU_SLL:  Y = A << B[4:0];
      ALU_SLT:  Y = {31'b0, $signed(A) < $signed(B)};
      ALU_SLTU: Y = {31'b0, A < B};
      ALU_XOR:  Y = A ^ B;
      ALU_SRL:  Y = A >> B[4:0];
      ALU_SRA:  Y = $unsigned($signed(A) >>> B[4:0]);
      ALU_OR:   Y = A | B;
      ALU_AND:  Y = A & B;
      default:  Y = 32'b0;
    endcase

endmodule
