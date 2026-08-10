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

  always_comb
    case (Funct3E)
      3'b000:  TakenE = (A == B);                    // beq
      3'b001:  TakenE = (A != B);                    // bne
      3'b100:  TakenE = ($signed(A) < $signed(B));   // blt
      3'b101:  TakenE = ($signed(A) >= $signed(B));  // bge
      3'b110:  TakenE = (A < B);                     // bltu
      3'b111:  TakenE = (A >= B);                    // bgeu
      default: TakenE = 1'b0;                        // reserved encodings
    endcase

endmodule
