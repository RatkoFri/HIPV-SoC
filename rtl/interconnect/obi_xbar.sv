///////////////////////////////////////////////////////////////////////
// obi_xbar
//
// Purpose: OBI crossbar for the HIPV SoC. Connects NUM_MASTERS master
//          ports to NUM_SLAVES slave ports so that accesses to
//          different slaves proceed concurrently.
//
//          Address phase: each master address is decoded to a one-hot
//          slave select; per slave, an obi_arbiter picks one of the
//          requesting masters and the winner's address/we/be/wdata are
//          muxed onto that slave port.
//
//          Response phase: OBI separates the address and response
//          phases, so the crossbar must remember where each master's
//          response will come from. Every master has a pending-slave
//          register loaded on grant; the response of that slave is
//          routed back to that master. This works because each HIPV
//          master keeps at most one transaction outstanding.
//
//          A slave is marked busy from grant until its response, so a
//          second master cannot start an access before the first one
//          has been answered. This suits the simple single-outstanding
//          memories and peripherals in this SoC.
//
//          Unmapped addresses are answered by an internal error
//          responder (grant immediately, rvalid with zero data one
//          cycle later) so a stray access never hangs the bus.
//
//          Ports are flattened packed vectors (master m occupies bits
//          [m*W +: W]) because the coding standard does not allow
//          arrays of signals as ports.
// Author:  Ratko Pilipovic
// Date:    12 August 2026
///////////////////////////////////////////////////////////////////////

// Parameter defaults come from hipv_soc_pkg, so adding a slave to the
// package resizes the crossbar (and every testbench) automatically.
module obi_xbar #(parameter NUM_MASTERS = hipv_soc_pkg::NUM_MASTERS,
                  parameter NUM_SLAVES  = hipv_soc_pkg::NUM_SLAVES,
                  parameter ARB_POLICY  = 0) (
  input  logic                        clk, reset,
  // master ports (flattened)
  input  logic [NUM_MASTERS-1:0]      MReq,
  output logic [NUM_MASTERS-1:0]      MGnt,
  input  logic [NUM_MASTERS*32-1:0]   MAddr,
  input  logic [NUM_MASTERS-1:0]      MWe,
  input  logic [NUM_MASTERS*4-1:0]    MBe,
  input  logic [NUM_MASTERS*32-1:0]   MWdata,
  output logic [NUM_MASTERS-1:0]      MRvalid,
  output logic [NUM_MASTERS*32-1:0]   MRdata,
  // slave ports (flattened)
  output logic [NUM_SLAVES-1:0]       SReq,
  input  logic [NUM_SLAVES-1:0]       SGnt,
  output logic [NUM_SLAVES*32-1:0]    SAddr,
  output logic [NUM_SLAVES-1:0]       SWe,
  output logic [NUM_SLAVES*4-1:0]     SBe,
  output logic [NUM_SLAVES*32-1:0]    SWdata,
  input  logic [NUM_SLAVES-1:0]       SRvalid,
  input  logic [NUM_SLAVES*32-1:0]    SRdata);

  localparam int unsigned SEL_W = (NUM_SLAVES > 1) ? $clog2(NUM_SLAVES) : 1;

  logic [NUM_SLAVES-1:0]   SlaveSel[NUM_MASTERS];   // one-hot, per master
  logic [NUM_MASTERS-1:0]  DecErr;
  logic [NUM_MASTERS-1:0]  SlaveReqM[NUM_SLAVES];   // requests per slave
  logic [NUM_MASTERS-1:0]  GrantM[NUM_SLAVES];      // one-hot grant per slave
  logic [NUM_SLAVES-1:0]   SlaveBusy;
  logic [NUM_MASTERS-1:0]  NormalGnt, ErrGnt, ErrPend;
  logic [SEL_W-1:0]        PendSlave[NUM_MASTERS];
  logic [NUM_MASTERS-1:0]  PendValid;

  // ---------------------------------------------------------------
  // address decode, one decoder per master
  // ---------------------------------------------------------------
  genvar m, s;
  generate
    for (m = 0; m < NUM_MASTERS; m++) begin : gen_decode
      obi_decoder dec(.Addr(MAddr[m*32 +: 32]), .SlaveSel(SlaveSel[m]),
                      .DecErr(DecErr[m]));
    end
  endgenerate

  // ---------------------------------------------------------------
  // per-slave arbitration and request muxing
  // ---------------------------------------------------------------
  generate
    for (s = 0; s < NUM_SLAVES; s++) begin : gen_slave
      // which masters are asking for this slave
      always_comb begin
        SlaveReqM[s] = '0;
        for (int i = 0; i < NUM_MASTERS; i++)
          SlaveReqM[s][i] = MReq[i] & SlaveSel[i][s] & ~DecErr[i];
      end

      obi_arbiter #(.NUM_MASTERS(NUM_MASTERS), .ARB_POLICY(ARB_POLICY))
        arb(.clk(clk), .reset(reset), .Req(SlaveReqM[s]),
            .Update(SReq[s] & SGnt[s]), .Grant(GrantM[s]));

      // a busy slave owes a response and must not be given a new access
      assign SReq[s] = |SlaveReqM[s] & ~SlaveBusy[s];

      always_ff @(posedge clk)
        if (reset) SlaveBusy[s] <= 1'b0;
        else if (SReq[s] & SGnt[s]) SlaveBusy[s] <= 1'b1;
        else if (SRvalid[s]) SlaveBusy[s] <= 1'b0;

      // drive the winning master's address phase onto the slave port
      always_comb begin
        SAddr[s*32 +: 32]  = '0;
        SWe[s]             = 1'b0;
        SBe[s*4 +: 4]      = '0;
        SWdata[s*32 +: 32] = '0;
        for (int i = 0; i < NUM_MASTERS; i++)
          if (GrantM[s][i]) begin
            SAddr[s*32 +: 32]  = MAddr[i*32 +: 32];
            SWe[s]             = MWe[i];
            SBe[s*4 +: 4]      = MBe[i*4 +: 4];
            SWdata[s*32 +: 32] = MWdata[i*32 +: 32];
          end
      end
    end
  endgenerate

  // ---------------------------------------------------------------
  // grants back to the masters
  // ---------------------------------------------------------------
  always_comb begin
    NormalGnt = '0;
    for (int i = 0; i < NUM_MASTERS; i++)
      for (int j = 0; j < NUM_SLAVES; j++)
        if (GrantM[j][i] & SReq[j] & SGnt[j]) NormalGnt[i] = 1'b1;
  end

  // unmapped address: grant at once, respond next cycle
  assign ErrGnt = MReq & DecErr & ~ErrPend;
  assign MGnt   = NormalGnt | ErrGnt;

  always_ff @(posedge clk)
    if (reset) ErrPend <= '0;
    else ErrPend <= ErrGnt;

  // ---------------------------------------------------------------
  // response routing: remember which slave owes each master an answer
  // ---------------------------------------------------------------
  generate
    for (m = 0; m < NUM_MASTERS; m++) begin : gen_response
      always_ff @(posedge clk)
        if (reset) begin
          PendValid[m] <= 1'b0;
          PendSlave[m] <= '0;
        end else if (NormalGnt[m]) begin
          PendValid[m] <= 1'b1;
          for (int j = 0; j < NUM_SLAVES; j++)
            if (GrantM[j][m] & SReq[j] & SGnt[j]) PendSlave[m] <= SEL_W'(j);
        end else if (MRvalid[m]) begin
          PendValid[m] <= 1'b0;
        end

      assign MRvalid[m] = (PendValid[m] & SRvalid[PendSlave[m]]) | ErrPend[m];
      assign MRdata[m*32 +: 32] = ErrPend[m] ? 32'b0
                                             : SRdata[PendSlave[m]*32 +: 32];
    end
  endgenerate

endmodule
