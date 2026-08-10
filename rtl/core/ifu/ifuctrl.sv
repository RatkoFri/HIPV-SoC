///////////////////////////////////////////////////////////////////////
// ifuctrl
//
// Purpose: Control FSM for the Instruction Fetch Unit.
//          One OBI transaction is outstanding at a time:
//            REQUEST   - drive ObiReqF, wait for ObiGntF
//            WAIT_RESP - wait for ObiRvalidF, capture the instruction
//            DONE      - present the instruction (ValidF) until the
//                        Decode stage takes it (ReadyD)
//          A redirect (PCSrcE) loads the PC with the branch target,
//          kills ValidF and marks any outstanding response as stale
//          (DiscardF) so it is dropped when it arrives.
//          Simplification: a redirect during REQUEST before ObiGntF
//          changes ObiAddrF while ObiReqF is high; a fully compliant
//          OBI master would keep the address phase stable.
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module ifuctrl (input  logic clk, reset,
                input  logic ObiGntF, ObiRvalidF,
                input  logic ReadyD, PCSrcE,
                output logic ObiReqF, PCEnF, InstrEnF, ValidF);

  typedef enum logic [1:0] {REQUEST, WAIT_RESP, DONE} statetype;

  statetype State, NextState;
  logic     DiscardF;

  // state register
  always_ff @(posedge clk)
    if (reset) State <= REQUEST;
    else State <= NextState;

  // next state logic
  always_comb
    case (State)
      REQUEST:   NextState = ObiGntF ? WAIT_RESP : REQUEST;
      WAIT_RESP: if (ObiRvalidF) NextState = (DiscardF | PCSrcE) ? REQUEST : DONE;
                 else NextState = WAIT_RESP;
      DONE:      NextState = (PCSrcE | ReadyD) ? REQUEST : DONE;
      default:   NextState = REQUEST;
    endcase

  // a redirect while a transaction is outstanding marks its response as stale
  always_ff @(posedge clk)
    if (reset) DiscardF <= 1'b0;
    else if (ObiRvalidF) DiscardF <= 1'b0;
    else if (PCSrcE & ((State == WAIT_RESP) | ((State == REQUEST) & ObiGntF)))
      DiscardF <= 1'b1;

  // outputs
  assign ObiReqF  = (State == REQUEST);
  assign PCEnF    = PCSrcE | ((State == DONE) & ReadyD);
  assign InstrEnF = (State == WAIT_RESP) & ObiRvalidF & ~DiscardF & ~PCSrcE;
  assign ValidF   = (State == DONE) & ~PCSrcE;

endmodule
