///////////////////////////////////////////////////////////////////////
// alu
//
// Purpose: Arithmetic-logic unit for the HIPV core. Implements the
//          RV32I integer operations plus the Zba/Zbb subset selected
//          by ALUControl (encoding in hipv_pkg). Shift and rotate
//          amounts are B[4:0].
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module alu (input  logic [31:0] A, B,
            input  logic [4:0]  ALUControl,
            output logic [31:0] Y);

  import hipv_pkg::*;

  logic [5:0]  Clz, Ctz, Cpop;
  logic [31:0] Rol, Ror;

  // count leading/trailing zeros and population count
  always_comb begin
    Clz  = 6'd32;
    Ctz  = 6'd32;
    Cpop = 6'd0;
    for (int i = 0; i < 32; i++) begin
      if (A[i]) Clz = 6'(31 - i);
      if (A[31 - i]) Ctz = 6'(31 - i);
      Cpop = Cpop + {5'b0, A[i]};
    end
  end

  assign Rol = (A << B[4:0]) | (A >> (6'd32 - {1'b0, B[4:0]}));
  assign Ror = (A >> B[4:0]) | (A << (6'd32 - {1'b0, B[4:0]}));

  always_comb
    case (ALUControl)
      ALU_ADD:    Y = A + B;
      ALU_SUB:    Y = A - B;
      ALU_SLL:    Y = A << B[4:0];
      ALU_SLT:    Y = {31'b0, $signed(A) < $signed(B)};
      ALU_SLTU:   Y = {31'b0, A < B};
      ALU_XOR:    Y = A ^ B;
      ALU_SRL:    Y = A >> B[4:0];
      ALU_SRA:    Y = $unsigned($signed(A) >>> B[4:0]);
      ALU_OR:     Y = A | B;
      ALU_AND:    Y = A & B;
      ALU_SH1ADD: Y = {A[30:0], 1'b0} + B;
      ALU_SH2ADD: Y = {A[29:0], 2'b0} + B;
      ALU_SH3ADD: Y = {A[28:0], 3'b0} + B;
      ALU_ANDN:   Y = A & ~B;
      ALU_ORN:    Y = A | ~B;
      ALU_XNOR:   Y = ~(A ^ B);
      ALU_MIN:    Y = ($signed(A) < $signed(B)) ? A : B;
      ALU_MINU:   Y = (A < B) ? A : B;
      ALU_MAX:    Y = ($signed(A) < $signed(B)) ? B : A;
      ALU_MAXU:   Y = (A < B) ? B : A;
      ALU_CLZ:    Y = {26'b0, Clz};
      ALU_CPOP:   Y = {26'b0, Cpop};
      ALU_CTZ:    Y = {26'b0, Ctz};
      ALU_SEXTB:  Y = {{24{A[7]}}, A[7:0]};
      ALU_SEXTH:  Y = {{16{A[15]}}, A[15:0]};
      ALU_ZEXTH:  Y = {16'b0, A[15:0]};
      ALU_ROL:    Y = Rol;
      ALU_ROR:    Y = Ror;
      ALU_ORCB:   Y = {{8{|A[31:24]}}, {8{|A[23:16]}}, {8{|A[15:8]}}, {8{|A[7:0]}}};
      ALU_REV8:   Y = {A[7:0], A[15:8], A[23:16], A[31:24]};
      default:    Y = 32'b0;
    endcase

endmodule
