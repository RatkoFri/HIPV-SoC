///////////////////////////////////////////////////////////////////////
// mul
//
// Purpose: Multi-cycle Zmmul multiplier (HW1 reference solution).
//          One 16x16 unsigned multiplier computes the four partial
//          products A_L*B_L, A_L*B_H, A_H*B_L, A_H*B_H in consecutive
//          cycles into a 64-bit accumulator. Signed operands are
//          handled by preloading the accumulator with the correction
//          -(a31*B + b31*A) << 32, which only affects the high word.
//          Interface contract: see the starter version of this file.
// Author:  HW1 reference solution
// Date:    6 October 2026
///////////////////////////////////////////////////////////////////////

module mul (input  logic        clk, reset,
            input  logic        Start, Ack,
            input  logic [31:0] A, B,
            input  logic [2:0]  Funct3,
            output logic        Busy, Done,
            output logic [31:0] Result);

  logic [31:0] AReg, BReg, CorrA, CorrB, Corr, PartialProduct;
  logic [15:0] AHalf, BHalf;
  logic [63:0] Acc, AccNext, AccInit, PPShifted;
  logic [1:0]  Step;
  logic        ASigned, BSigned, HighWord, AccEn;

  mulctrl ctrl(.clk(clk), .reset(reset), .Start(Start), .Ack(Ack),
               .Busy(Busy), .Done(Done), .AccEn(AccEn), .Step(Step));

  // operands are only valid in the Start cycle: capture them
  flopenr #(32) areg(.clk(clk), .reset(reset), .en(Start), .D(A), .Q(AReg));
  flopenr #(32) breg(.clk(clk), .reset(reset), .en(Start), .D(B), .Q(BReg));
  flopenr #(1)  hireg(.clk(clk), .reset(reset), .en(Start),
                      .D(Funct3 != 3'b000), .Q(HighWord));

  // sign correction: mulh (001) both signed, mulhsu (010) rs1 signed
  assign ASigned = (Funct3 == 3'b001) | (Funct3 == 3'b010);
  assign BSigned = (Funct3 == 3'b001);
  assign CorrA   = (ASigned & A[31]) ? B : 32'b0;
  assign CorrB   = (BSigned & B[31]) ? A : 32'b0;
  assign Corr    = CorrA + CorrB;
  assign AccInit = {32'b0 - Corr, 32'b0};

  // one 16x16 multiplier, halves selected by the step counter
  mux2 #(16) amux(.D0(AReg[15:0]), .D1(AReg[31:16]), .S(Step[1]), .Y(AHalf));
  mux2 #(16) bmux(.D0(BReg[15:0]), .D1(BReg[31:16]), .S(Step[0]), .Y(BHalf));
  assign PartialProduct = AHalf * BHalf;

  // shift by 0, 16 or 32: 16 times the number of high halves used
  always_comb
    case (Step)
      2'b00:   PPShifted = {32'b0, PartialProduct};
      2'b11:   PPShifted = {PartialProduct, 32'b0};
      default: PPShifted = {16'b0, PartialProduct, 16'b0};
    endcase

  mux2 #(64) accmux(.D0(Acc + PPShifted), .D1(AccInit), .S(Start), .Y(AccNext));
  flopenr #(64) accreg(.clk(clk), .reset(reset), .en(Start | AccEn), .D(AccNext), .Q(Acc));

  mux2 #(32) resmux(.D0(Acc[31:0]), .D1(Acc[63:32]), .S(HighWord), .Y(Result));

endmodule
