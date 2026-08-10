///////////////////////////////////////////////////////////////////////
// lsu
//
// Purpose: Load/Store Unit for the HIPV core (M stage).
//          Holds the E/M pipeline register. Non-memory instructions
//          pass through in one cycle. Loads and stores run one OBI
//          transaction on the data port (req/gnt, rvalid/rdata with
//          we/be/wdata for stores); the stage presents ValidM only
//          when the transaction is complete, so ReadyM back-pressures
//          the Execute stage during the access.
//          Byte/halfword accesses are aligned with byte enables and
//          the read data is shifted and sign/zero extended by funct3.
//          ForwardDataM feeds the forwarding mux in Execute: the load
//          data for loads, the ALU result otherwise.
//          Misaligned accesses are not detected (no traps yet).
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module lsu (input  logic        clk, reset,
            // handshake with the Execute stage
            input  logic        ValidE,
            output logic        ReadyM,
            // inputs from Execute
            input  logic [31:0] ALUResultE, WriteDataE, PCPlus4E,
            input  logic [4:0]  RdE,
            input  logic [2:0]  Funct3E,
            input  logic        RegWriteE, MemWriteE,
            input  logic [1:0]  ResultSrcE,
            // handshake with the Writeback stage
            output logic        ValidM,
            input  logic        ReadyW,
            // stage outputs to Writeback
            output logic [31:0] ALUResultM, ReadDataM, PCPlus4M,
            output logic [4:0]  RdM,
            output logic        RegWriteM,
            output logic [1:0]  ResultSrcM,
            // forwarding to Execute
            output logic [31:0] ForwardDataM,
            // OBI master port to data memory
            output logic        ObiReqM,
            input  logic        ObiGntM,
            output logic [31:0] ObiAddrM,
            output logic        ObiWeM,
            output logic [3:0]  ObiBeM,
            output logic [31:0] ObiWdataM,
            input  logic        ObiRvalidM,
            input  logic [31:0] ObiRdataM);

  import hipv_pkg::*;

  logic        ValidMReg, EnEM, MemOpM, DoneM, WaitRespM, CaptureM;
  logic        RegWriteMReg, MemWriteM;
  logic [2:0]  Funct3M;
  logic [31:0] WriteDataM, ReadRawM, ReadShiftM;
  logic [1:0]  AddrLsbM;

  // E/M handshake: a memory instruction holds the stage until done
  assign MemOpM = MemWriteM | (ResultSrcM == RESULT_MEM);
  assign ValidM = ValidMReg & (~MemOpM | DoneM);
  assign ReadyM = ~ValidMReg | (ValidM & ReadyW);
  assign EnEM   = ValidE & ReadyM;

  // E/M valid bit
  always_ff @(posedge clk)
    if (reset) ValidMReg <= 1'b0;
    else if (ReadyM) ValidMReg <= ValidE;

  // E/M pipeline registers
  flopenr #(32) alureg(.clk(clk), .reset(reset), .en(EnEM), .D(ALUResultE), .Q(ALUResultM));
  flopenr #(32) wdreg(.clk(clk), .reset(reset), .en(EnEM), .D(WriteDataE), .Q(WriteDataM));
  flopenr #(32) pcplus4reg(.clk(clk), .reset(reset), .en(EnEM), .D(PCPlus4E), .Q(PCPlus4M));
  flopenr #(5)  rdreg(.clk(clk), .reset(reset), .en(EnEM), .D(RdE), .Q(RdM));
  flopenr #(3)  funct3reg(.clk(clk), .reset(reset), .en(EnEM), .D(Funct3E), .Q(Funct3M));
  flopenr #(4)  ctrlreg(.clk(clk), .reset(reset), .en(EnEM),
                        .D({RegWriteE, MemWriteE, ResultSrcE}),
                        .Q({RegWriteMReg, MemWriteM, ResultSrcM}));

  // OBI transaction control: one outstanding request per instruction
  assign ObiReqM  = ValidMReg & MemOpM & ~DoneM & ~WaitRespM;
  assign CaptureM = WaitRespM & ObiRvalidM;

  always_ff @(posedge clk)
    if (reset) WaitRespM <= 1'b0;
    else if (~WaitRespM & ObiReqM & ObiGntM) WaitRespM <= 1'b1;
    else if (CaptureM) WaitRespM <= 1'b0;

  always_ff @(posedge clk)
    if (reset) DoneM <= 1'b0;
    else if (EnEM) DoneM <= 1'b0;
    else if (CaptureM) DoneM <= 1'b1;

  // raw read data register
  flopenr #(32) rawreg(.clk(clk), .reset(reset), .en(CaptureM), .D(ObiRdataM), .Q(ReadRawM));

  // address phase: word-aligned address, byte enables from size and offset
  assign AddrLsbM = ALUResultM[1:0];
  assign ObiAddrM = {ALUResultM[31:2], 2'b00};
  assign ObiWeM   = MemWriteM;
  assign ObiWdataM = WriteDataM << {AddrLsbM, 3'b000};

  always_comb
    case (Funct3M[1:0])
      2'b00:   ObiBeM = 4'b0001 << AddrLsbM;              // sb/lb
      2'b01:   ObiBeM = AddrLsbM[1] ? 4'b1100 : 4'b0011;  // sh/lh
      default: ObiBeM = 4'b1111;                          // sw/lw
    endcase

  // read data alignment and sign/zero extension
  assign ReadShiftM = ReadRawM >> {AddrLsbM, 3'b000};

  always_comb
    case (Funct3M)
      3'b000:  ReadDataM = {{24{ReadShiftM[7]}}, ReadShiftM[7:0]};    // lb
      3'b001:  ReadDataM = {{16{ReadShiftM[15]}}, ReadShiftM[15:0]};  // lh
      3'b100:  ReadDataM = {24'b0, ReadShiftM[7:0]};                  // lbu
      3'b101:  ReadDataM = {16'b0, ReadShiftM[15:0]};                 // lhu
      default: ReadDataM = ReadShiftM;                                // lw
    endcase

  // forwarding data for the Execute stage: load data or ALU result
  assign ForwardDataM = (ResultSrcM == RESULT_MEM) ? ReadDataM : ALUResultM;

  // register write indication, qualified with the stage valid bit
  assign RegWriteM = RegWriteMReg & ValidMReg;

endmodule
