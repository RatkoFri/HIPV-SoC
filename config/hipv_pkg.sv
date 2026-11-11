///////////////////////////////////////////////////////////////////////
// hipv_pkg
//
// Purpose: Shared constants for the HIPV core: control signal
//          encodings and RV32I opcodes. Imported by decode and
//          execute logic so both sides agree on the encodings.
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

// not every unit uses every constant; that is fine for a shared package
/* verilator lint_off UNUSEDPARAM */
package hipv_pkg;

  // ALU operation encoding (ALUControl)
  localparam logic [4:0] ALU_ADD  = 5'b00000;
  localparam logic [4:0] ALU_SUB  = 5'b00001;
  localparam logic [4:0] ALU_SLL  = 5'b00010;
  localparam logic [4:0] ALU_SLT  = 5'b00011;
  localparam logic [4:0] ALU_SLTU = 5'b00100;
  localparam logic [4:0] ALU_XOR  = 5'b00101;
  localparam logic [4:0] ALU_SRL  = 5'b00110;
  localparam logic [4:0] ALU_SRA  = 5'b00111;
  localparam logic [4:0] ALU_OR   = 5'b01000;
  localparam logic [4:0] ALU_AND  = 5'b01001;
  // Zba / Zbb (homework 1, Task 1)
  localparam logic [4:0] ALU_SH1ADD = 5'b01010;
  localparam logic [4:0] ALU_SH2ADD = 5'b01011;
  localparam logic [4:0] ALU_SH3ADD = 5'b01100;
  localparam logic [4:0] ALU_ANDN   = 5'b01101;
  localparam logic [4:0] ALU_ORN    = 5'b01110;
  localparam logic [4:0] ALU_XNOR   = 5'b01111;
  localparam logic [4:0] ALU_MIN    = 5'b10000;
  localparam logic [4:0] ALU_MINU   = 5'b10001;
  localparam logic [4:0] ALU_MAX    = 5'b10010;
  localparam logic [4:0] ALU_MAXU   = 5'b10011;
  localparam logic [4:0] ALU_CLZ    = 5'b10100;
  localparam logic [4:0] ALU_CPOP   = 5'b10101;
  localparam logic [4:0] ALU_CTZ    = 5'b10110;
  localparam logic [4:0] ALU_SEXTB  = 5'b10111;
  localparam logic [4:0] ALU_SEXTH  = 5'b11000;
  localparam logic [4:0] ALU_ZEXTH  = 5'b11001;
  localparam logic [4:0] ALU_ROL    = 5'b11010;
  localparam logic [4:0] ALU_ROR    = 5'b11011;
  localparam logic [4:0] ALU_ORCB   = 5'b11100;
  localparam logic [4:0] ALU_REV8   = 5'b11101;

  // immediate format select (ImmSrc)
  localparam logic [2:0] IMM_I = 3'b000;
  localparam logic [2:0] IMM_S = 3'b001;
  localparam logic [2:0] IMM_B = 3'b010;
  localparam logic [2:0] IMM_J = 3'b011;
  localparam logic [2:0] IMM_U = 3'b100;

  // writeback result select (ResultSrc)
  localparam logic [1:0] RESULT_ALU = 2'b00;
  localparam logic [1:0] RESULT_MEM = 2'b01;
  localparam logic [1:0] RESULT_PC4 = 2'b10;

  // ALU operand A select (ALUSrcA)
  localparam logic [1:0] SRCA_RF   = 2'b00;  // register file RD1
  localparam logic [1:0] SRCA_PC   = 2'b01;  // PC (auipc)
  localparam logic [1:0] SRCA_ZERO = 2'b10;  // zero (lui)

  // forwarding select (ForwardAE / ForwardBE, from the hazard unit)
  localparam logic [1:0] FWD_RF  = 2'b00;  // register operand from D/E register
  localparam logic [1:0] FWD_WB  = 2'b01;  // ResultW from the Writeback stage
  localparam logic [1:0] FWD_MEM = 2'b10;  // ForwardDataM from the Memory stage

  // RV32I opcodes
  localparam logic [6:0] OP_RTYPE  = 7'b0110011;
  localparam logic [6:0] OP_IALU   = 7'b0010011;
  localparam logic [6:0] OP_LOAD   = 7'b0000011;
  localparam logic [6:0] OP_STORE  = 7'b0100011;
  localparam logic [6:0] OP_BRANCH = 7'b1100011;
  localparam logic [6:0] OP_JAL    = 7'b1101111;
  localparam logic [6:0] OP_JALR   = 7'b1100111;
  localparam logic [6:0] OP_LUI    = 7'b0110111;
  localparam logic [6:0] OP_AUIPC  = 7'b0010111;

endpackage
/* verilator lint_on UNUSEDPARAM */
