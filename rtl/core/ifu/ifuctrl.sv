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
//          State and DiscardF are both held in the same current/next
//          pair, so the decision in WAIT_RESP is taken on the current
//          DiscardF while its clear is scheduled for the next cycle.
//          Simplification: a redirect during REQUEST before ObiGntF
//          changes ObiAddrF while ObiReqF is high; a fully compliant
//          OBI master would keep the address phase stable.
// Author:  Ratko Pilipovic
// Date:    10 August 2026
///////////////////////////////////////////////////////////////////////

module ifuctrl (input  logic clk, reset,
                input  logic ObiGntF, ObiRvalidF, // From OBI memory
                input  logic ReadyD, PCSrcE,  // From Decode and Execute
                output logic ObiReqF, PCEnF, InstrEnF, ValidF);

  typedef enum logic [1:0] {REQUEST, WAIT_RESP, DONE} statetype;

  statetype State, NextState;
  logic     DiscardF, NextDiscardF;

  // state register
  always_ff @(posedge clk)
    if (reset) begin
      State    <= REQUEST;
      DiscardF <= 1'b0;
    end else begin
      State    <= NextState;
      DiscardF <= NextDiscardF;
    end

  // next state logic
  always_comb begin
    NextState    = State;  // defaults: hold
    NextDiscardF = DiscardF;
    case (State)
      // the grant commits the transaction on this edge, so a redirect
      // in the same cycle already has a wrong-path response coming
      REQUEST:   begin NextState    = ObiGntF ? WAIT_RESP : REQUEST;
                       NextDiscardF = ObiGntF & PCSrcE; end
      // the awaited response clears the flag; with no response yet, a
      // redirect makes the outstanding one stale
      WAIT_RESP: if (ObiRvalidF) begin NextState    = (DiscardF | PCSrcE) ? REQUEST : DONE;
                                       NextDiscardF = 1'b0; end
                 else NextDiscardF = DiscardF | PCSrcE;
      DONE:      if (PCSrcE | ReadyD) NextState = REQUEST;
      default:   NextState = REQUEST;
    endcase
  end

  // outputs
  assign ObiReqF  = (State == REQUEST);
  assign PCEnF    = PCSrcE | ((State == DONE) & ReadyD);
  assign InstrEnF = (State == WAIT_RESP) & ObiRvalidF & ~DiscardF & ~PCSrcE;
  assign ValidF   = (State == DONE) & ~PCSrcE;

endmodule
