///////////////////////////////////////////////////////////////////////
// hipv_core
//
// Purpose: HIPV top level: 5-stage pipelined RV32I core.
//          Connects the pipeline stages (ifu, idu, ieu, lsu, wbu) via
//          valid/ready handshakes and the hazard unit (forwarding).
//          Two OBI master ports: instruction fetch (read-only) and
//          data (read/write).
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module hipv_core (input  logic        clk, reset,
                  // OBI instruction port
                  output logic        ObiIReq,
                  input  logic        ObiIGnt,
                  output logic [31:0] ObiIAddr,
                  input  logic        ObiIRvalid,
                  input  logic [31:0] ObiIRdata,
                  // OBI data port
                  output logic        ObiDReq,
                  input  logic        ObiDGnt,
                  output logic [31:0] ObiDAddr,
                  output logic        ObiDWe,
                  output logic [3:0]  ObiDBe,
                  output logic [31:0] ObiDWdata,
                  input  logic        ObiDRvalid,
                  input  logic [31:0] ObiDRdata);

  // F <-> D
  logic        ValidF, ReadyD;
  logic [31:0] InstrF, PCF, PCPlus4F;
  // D <-> E
  logic        ValidD, ReadyE;
  logic [31:0] RD1D, RD2D, ImmExtD, PCD, PCPlus4D;
  logic [4:0]  Rs1D, Rs2D, RdD;
  logic [2:0]  Funct3D;
  logic        RegWriteD, MemWriteD, BranchD, JumpD, JalrD, ALUSrcBD;
  logic [1:0]  ResultSrcD, ALUSrcAD;
  logic [3:0]  ALUControlD;
  // E <-> M
  logic        ValidE, ReadyM;
  logic [31:0] ALUResultE, WriteDataE, PCPlus4E;
  logic [4:0]  RdE, Rs1E, Rs2E;
  logic [2:0]  Funct3E;
  logic        RegWriteE, MemWriteE;
  logic [1:0]  ResultSrcE;
  // redirect
  logic        PCSrcE;
  logic [31:0] PCTargetE;
  // M <-> W
  logic        ValidM, ReadyW;
  logic [31:0] ALUResultM, ReadDataM, PCPlus4M, ForwardDataM;
  logic [4:0]  RdM;
  logic        RegWriteM;
  logic [1:0]  ResultSrcM;
  // W outputs. ValidW marks instruction retirement: nothing in the core
  // consumes it (RegWriteW is already valid-qualified), but it is kept
  // as a retirement marker for waveform debugging and as the hook for a
  // future trace/RVFI port.
  /* verilator lint_off UNUSEDSIGNAL */
  logic        ValidW;
  /* verilator lint_on UNUSEDSIGNAL */
  logic        RegWriteW;
  logic [4:0]  RdW;
  logic [31:0] ResultW;
  // forwarding
  logic [1:0]  ForwardAE, ForwardBE;

  // Fetch
  ifu ifu(.clk(clk), .reset(reset),
          .ReadyD(ReadyD), .ValidF(ValidF),
          .PCSrcE(PCSrcE), .PCTargetE(PCTargetE),
          .InstrF(InstrF), .PCF(PCF), .PCPlus4F(PCPlus4F),
          .ObiReqF(ObiIReq), .ObiGntF(ObiIGnt), .ObiAddrF(ObiIAddr),
          .ObiRvalidF(ObiIRvalid), .ObiRdataF(ObiIRdata));

  // Decode
  idu idu(.clk(clk), .reset(reset),
          .ValidF(ValidF), .ReadyD(ReadyD),
          .InstrF(InstrF), .PCF(PCF), .PCPlus4F(PCPlus4F),
          .PCSrcE(PCSrcE),
          .ValidD(ValidD), .ReadyE(ReadyE),
          .RegWriteW(RegWriteW), .RdW(RdW), .ResultW(ResultW),
          .RD1D(RD1D), .RD2D(RD2D), .ImmExtD(ImmExtD), .PCD(PCD), .PCPlus4D(PCPlus4D),
          .Rs1D(Rs1D), .Rs2D(Rs2D), .RdD(RdD), .Funct3D(Funct3D),
          .RegWriteD(RegWriteD), .MemWriteD(MemWriteD), .BranchD(BranchD),
          .JumpD(JumpD), .JalrD(JalrD), .ResultSrcD(ResultSrcD),
          .ALUSrcAD(ALUSrcAD), .ALUSrcBD(ALUSrcBD), .ALUControlD(ALUControlD));

  // Execute
  ieu ieu(.clk(clk), .reset(reset),
          .ValidD(ValidD), .ReadyE(ReadyE),
          .RD1D(RD1D), .RD2D(RD2D), .ImmExtD(ImmExtD), .PCD(PCD), .PCPlus4D(PCPlus4D),
          .Rs1D(Rs1D), .Rs2D(Rs2D), .RdD(RdD), .Funct3D(Funct3D),
          .RegWriteD(RegWriteD), .MemWriteD(MemWriteD), .BranchD(BranchD),
          .JumpD(JumpD), .JalrD(JalrD), .ResultSrcD(ResultSrcD),
          .ALUSrcAD(ALUSrcAD), .ALUSrcBD(ALUSrcBD), .ALUControlD(ALUControlD),
          .ForwardAE(ForwardAE), .ForwardBE(ForwardBE),
          .ForwardDataM(ForwardDataM), .ResultW(ResultW),
          .PCSrcE(PCSrcE), .PCTargetE(PCTargetE),
          .ValidE(ValidE), .ReadyM(ReadyM),
          .ALUResultE(ALUResultE), .WriteDataE(WriteDataE), .PCPlus4E(PCPlus4E),
          .RdE(RdE), .Rs1E(Rs1E), .Rs2E(Rs2E), .Funct3E(Funct3E),
          .RegWriteE(RegWriteE), .MemWriteE(MemWriteE), .ResultSrcE(ResultSrcE));

  // Memory
  lsu lsu(.clk(clk), .reset(reset),
          .ValidE(ValidE), .ReadyM(ReadyM),
          .ALUResultE(ALUResultE), .WriteDataE(WriteDataE), .PCPlus4E(PCPlus4E),
          .RdE(RdE), .Funct3E(Funct3E),
          .RegWriteE(RegWriteE), .MemWriteE(MemWriteE), .ResultSrcE(ResultSrcE),
          .ValidM(ValidM), .ReadyW(ReadyW),
          .ALUResultM(ALUResultM), .ReadDataM(ReadDataM), .PCPlus4M(PCPlus4M),
          .RdM(RdM), .RegWriteM(RegWriteM), .ResultSrcM(ResultSrcM),
          .ForwardDataM(ForwardDataM),
          .ObiReqM(ObiDReq), .ObiGntM(ObiDGnt), .ObiAddrM(ObiDAddr),
          .ObiWeM(ObiDWe), .ObiBeM(ObiDBe), .ObiWdataM(ObiDWdata),
          .ObiRvalidM(ObiDRvalid), .ObiRdataM(ObiDRdata));

  // Writeback
  wbu wbu(.clk(clk), .reset(reset),
          .ValidM(ValidM), .ReadyW(ReadyW),
          .ALUResultM(ALUResultM), .ReadDataM(ReadDataM), .PCPlus4M(PCPlus4M),
          .RdM(RdM), .RegWriteM(RegWriteM), .ResultSrcM(ResultSrcM),
          .ValidW(ValidW), .RegWriteW(RegWriteW), .RdW(RdW), .ResultW(ResultW));

  // Hazard unit (forwarding)
  hazard hz(.Rs1E(Rs1E), .Rs2E(Rs2E), .RdM(RdM), .RdW(RdW),
            .RegWriteM(RegWriteM), .RegWriteW(RegWriteW),
            .ForwardAE(ForwardAE), .ForwardBE(ForwardBE));

endmodule
