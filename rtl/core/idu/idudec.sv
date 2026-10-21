///////////////////////////////////////////////////////////////////////
// idudec
//
// Purpose: Control decoder for the Decode stage. The main decoder
//          maps the opcode to a control word; the ALU decoder refines
//          ALUControlD from funct3/funct7 for R-type and I-type ALU
//          instructions. jalr computes its target on the ALU
//          (rs1 + imm); branch and jal targets use the dedicated
//          PC + imm adder in Execute.
//          Unimplemented opcodes (fence, system, ...) decode to an
//          all-zero control word and pass through as a nop.
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module idudec (input  logic [6:0] OpD,
               input  logic [2:0] Funct3D,
               input  logic       Funct7b5D,
               output logic       RegWriteD,
               output logic [2:0] ImmSrcD,
               output logic [1:0] ALUSrcAD,
               output logic       ALUSrcBD,
               output logic       MemWriteD,
               output logic [1:0] ResultSrcD,
               output logic       BranchD, JumpD, JalrD,
               output logic [3:0] ALUControlD);

  // 0. import hipv_pkg::* (OP_*, IMM_*, SRCA_*, RESULT_*, ALU_*)
  //    Internal signals: ControlsD [14:0], ALUOpD [1:0], RtypeSubD

  // 1. Unpack the control word with one concatenation assign:
  //      {RegWriteD, ImmSrcD, ALUSrcAD, ALUSrcBD, MemWriteD, ResultSrcD,
  //       BranchD, JumpD, JalrD, ALUOpD} = ControlsD

  // 2. Main decoder: always_comb case (OpD)
  //               RegWrite ImmSrc SrcA       SrcB MemWrite ResultSrc  Branch Jump Jalr ALUOp
  //    OP_RTYPE   1        IMM_I  SRCA_RF    0    0        RESULT_ALU 0      0    0    10
  //    OP_IALU    1        IMM_I  SRCA_RF    1    0        RESULT_ALU 0      0    0    10
  //    OP_LOAD    1        IMM_I  SRCA_RF    1    0        RESULT_MEM 0      0    0    00
  //    OP_STORE   0        IMM_S  SRCA_RF    1    1        RESULT_ALU 0      0    0    00
  //    OP_BRANCH  0        IMM_B  SRCA_RF    0    0        RESULT_ALU 1      0    0    01
  //    OP_JAL     1        IMM_J  SRCA_RF    0    0        RESULT_PC4 0      1    0    00
  //    OP_JALR    1        IMM_I  SRCA_RF    1    0        RESULT_PC4 0      0    1    00
  //    OP_LUI     1        IMM_U  SRCA_ZERO  1    0        RESULT_ALU 0      0    0    00
  //    OP_AUIPC   1        IMM_U  SRCA_PC    1    0        RESULT_ALU 0      0    0    00
  //    default:   all zeros (unimplemented opcode -> nop)
  //    (ImmSrc of R-type is a don't care; use IMM_I)

  // 3. RtypeSubD = Funct7b5D & OpD[5]
  //    sub exists only as R-type; addi with imm[10] = 1 must stay an add

  // 4. ALU decoder: always_comb
  //    if ALUOpD == 2'b10, case (Funct3D):
  //      000 -> RtypeSubD ? ALU_SUB : ALU_ADD
  //      001 -> ALU_SLL       010 -> ALU_SLT       011 -> ALU_SLTU
  //      100 -> ALU_XOR       101 -> Funct7b5D ? ALU_SRA : ALU_SRL
  //      110 -> ALU_OR        111 -> ALU_AND
  //    else ALU_ADD (address and jalr target computation)

endmodule
