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
  localparam logic [3:0] ALU_ADD  = 4'b0000;
  localparam logic [3:0] ALU_SUB  = 4'b0001;
  localparam logic [3:0] ALU_SLL  = 4'b0010;
  localparam logic [3:0] ALU_SLT  = 4'b0011;
  localparam logic [3:0] ALU_SLTU = 4'b0100;
  localparam logic [3:0] ALU_XOR  = 4'b0101;
  localparam logic [3:0] ALU_SRL  = 4'b0110;
  localparam logic [3:0] ALU_SRA  = 4'b0111;
  localparam logic [3:0] ALU_OR   = 4'b1000;
  localparam logic [3:0] ALU_AND  = 4'b1001;

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
