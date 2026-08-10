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

  import hipv_pkg::*;

  logic [14:0] ControlsD;
  logic [1:0]  ALUOpD;
  logic        RtypeSubD;

  assign {RegWriteD, ImmSrcD, ALUSrcAD, ALUSrcBD, MemWriteD, ResultSrcD,
          BranchD, JumpD, JalrD, ALUOpD} = ControlsD;

  // main decoder
  //                        RegWrite ImmSrc SrcA       SrcB  MemWrite ResultSrc   Branch Jump  Jalr  ALUOp
  always_comb
    case (OpD)
      OP_RTYPE:  ControlsD = {1'b1, IMM_I, SRCA_RF,   1'b0, 1'b0, RESULT_ALU, 1'b0, 1'b0, 1'b0, 2'b10};
      OP_IALU:   ControlsD = {1'b1, IMM_I, SRCA_RF,   1'b1, 1'b0, RESULT_ALU, 1'b0, 1'b0, 1'b0, 2'b10};
      OP_LOAD:   ControlsD = {1'b1, IMM_I, SRCA_RF,   1'b1, 1'b0, RESULT_MEM, 1'b0, 1'b0, 1'b0, 2'b00};
      OP_STORE:  ControlsD = {1'b0, IMM_S, SRCA_RF,   1'b1, 1'b1, RESULT_ALU, 1'b0, 1'b0, 1'b0, 2'b00};
      OP_BRANCH: ControlsD = {1'b0, IMM_B, SRCA_RF,   1'b0, 1'b0, RESULT_ALU, 1'b1, 1'b0, 1'b0, 2'b01};
      OP_JAL:    ControlsD = {1'b1, IMM_J, SRCA_RF,   1'b0, 1'b0, RESULT_PC4, 1'b0, 1'b1, 1'b0, 2'b00};
      OP_JALR:   ControlsD = {1'b1, IMM_I, SRCA_RF,   1'b1, 1'b0, RESULT_PC4, 1'b0, 1'b0, 1'b1, 2'b00};
      OP_LUI:    ControlsD = {1'b1, IMM_U, SRCA_ZERO, 1'b1, 1'b0, RESULT_ALU, 1'b0, 1'b0, 1'b0, 2'b00};
      OP_AUIPC:  ControlsD = {1'b1, IMM_U, SRCA_PC,   1'b1, 1'b0, RESULT_ALU, 1'b0, 1'b0, 1'b0, 2'b00};
      default:   ControlsD = 15'b0;  // unimplemented opcode: nop
    endcase

  // sub only exists as an R-type encoding (addi has no subi)
  assign RtypeSubD = Funct7b5D & OpD[5];

  // ALU decoder
  always_comb
    if (ALUOpD == 2'b10)
      case (Funct3D)
        3'b000:  ALUControlD = RtypeSubD ? ALU_SUB : ALU_ADD;
        3'b001:  ALUControlD = ALU_SLL;
        3'b010:  ALUControlD = ALU_SLT;
        3'b011:  ALUControlD = ALU_SLTU;
        3'b100:  ALUControlD = ALU_XOR;
        3'b101:  ALUControlD = Funct7b5D ? ALU_SRA : ALU_SRL;
        3'b110:  ALUControlD = ALU_OR;
        default: ALUControlD = ALU_AND;
      endcase
    else ALUControlD = ALU_ADD;  // address / target computation

endmodule
