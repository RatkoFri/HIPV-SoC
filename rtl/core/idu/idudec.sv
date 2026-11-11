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
               input  logic [6:0] Funct7D,
               input  logic [4:0] Rs2D,
               output logic       RegWriteD,
               output logic [2:0] ImmSrcD,
               output logic [1:0] ALUSrcAD,
               output logic       ALUSrcBD,
               output logic       MemWriteD,
               output logic [1:0] ResultSrcD,
               output logic       BranchD, JumpD, JalrD, MulD,
               output logic [4:0] ALUControlD);

  import hipv_pkg::*;

  logic [14:0] ControlsD;
  logic [1:0]  ALUOpD;
  logic        RtypeSubD, RegWriteMainD, MExtD;

  assign {RegWriteMainD, ImmSrcD, ALUSrcAD, ALUSrcBD, MemWriteD, ResultSrcD,
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

  // M-extension encodings: mul* go to the multiplier; div/rem are not
  // part of Zmmul and decode as nops (no register write)
  assign MExtD     = (OpD == OP_RTYPE) & (Funct7D == 7'b0000001);
  assign MulD      = MExtD & ~Funct3D[2];
  assign RegWriteD = RegWriteMainD & ~(MExtD & Funct3D[2]);

  // sub only exists as an R-type encoding (addi has no subi)
  assign RtypeSubD = Funct7D[5] & OpD[5];

  // ALU decoder: Zba/Zbb encodings first (they reuse RV32I funct3
  // values and are told apart by funct7, and by rs2 for the unary
  // ops), then the RV32I operations by funct3
  // the casez is a priority decoder: the overlap is intentional
  /* verilator lint_off CASEOVERLAP */
  always_comb
    if (ALUOpD != 2'b10) ALUControlD = ALU_ADD;  // address / target computation
    else
      casez ({OpD[5], Funct7D, Funct3D})
        11'b1_0010000_010: ALUControlD = ALU_SH1ADD;
        11'b1_0010000_100: ALUControlD = ALU_SH2ADD;
        11'b1_0010000_110: ALUControlD = ALU_SH3ADD;
        11'b1_0100000_111: ALUControlD = ALU_ANDN;
        11'b1_0100000_110: ALUControlD = ALU_ORN;
        11'b1_0100000_100: ALUControlD = ALU_XNOR;
        11'b1_0000101_100: ALUControlD = ALU_MIN;
        11'b1_0000101_101: ALUControlD = ALU_MINU;
        11'b1_0000101_110: ALUControlD = ALU_MAX;
        11'b1_0000101_111: ALUControlD = ALU_MAXU;
        11'b1_0000100_100: ALUControlD = ALU_ZEXTH;
        11'b1_0110000_001: ALUControlD = ALU_ROL;
        11'b1_0110000_101: ALUControlD = ALU_ROR;
        11'b0_0110000_101: ALUControlD = ALU_ROR;   // rori
        11'b0_0010100_101: ALUControlD = ALU_ORCB;
        11'b0_0110100_101: ALUControlD = ALU_REV8;
        11'b0_0110000_001:
          case (Rs2D)
            5'b00000: ALUControlD = ALU_CLZ;
            5'b00001: ALUControlD = ALU_CTZ;
            5'b00010: ALUControlD = ALU_CPOP;
            5'b00100: ALUControlD = ALU_SEXTB;
            default:  ALUControlD = ALU_SEXTH;
          endcase
        11'b?_???????_000: ALUControlD = RtypeSubD ? ALU_SUB : ALU_ADD;
        11'b?_???????_001: ALUControlD = ALU_SLL;
        11'b?_???????_010: ALUControlD = ALU_SLT;
        11'b?_???????_011: ALUControlD = ALU_SLTU;
        11'b?_???????_100: ALUControlD = ALU_XOR;
        11'b?_???????_101: ALUControlD = Funct7D[5] ? ALU_SRA : ALU_SRL;
        11'b?_???????_110: ALUControlD = ALU_OR;
        default:           ALUControlD = ALU_AND;
      endcase
  /* verilator lint_on CASEOVERLAP */

endmodule
