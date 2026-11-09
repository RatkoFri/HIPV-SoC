///////////////////////////////////////////////////////////////////////
// lsuctrl
//
// Purpose: Control FSM for the Load/Store Unit.
//          One OBI transaction per memory instruction, at most one
//          outstanding:
//            IDLE      - a memory instruction in M drives ObiReqM
//                        and waits for ObiGntM
//            WAIT_RESP - wait for ObiRvalidM, capture the read data
//            DONE      - present the result (DoneM) until the
//                        Writeback stage takes it (ReadyW)
//          Non-memory instructions never leave IDLE.
//          ObiReqM is a Mealy output in IDLE, so the request goes out
//          in the first cycle the instruction is in M.
// Author:  Ratko Pilipovic
// Date:    3 November 2026
///////////////////////////////////////////////////////////////////////

module lsuctrl (input  logic clk, reset,
                input  logic MemReqM,               // valid load/store in M
                input  logic ObiGntM, ObiRvalidM,   // From OBI memory
                input  logic ReadyW,                // From Writeback
                output logic ObiReqM, CaptureM, DoneM);

  typedef enum logic [1:0] {IDLE, WAIT_RESP, DONE} statetype;

  statetype State, NextState;

  // state register
  always_ff @(posedge clk)
    if (reset) State <= IDLE;
    else       State <= NextState;

  // next state logic
  always_comb begin
    NextState = State;  // default: hold
    case (State)
      IDLE:      if (MemReqM & ObiGntM) NextState = WAIT_RESP;
      WAIT_RESP: if (ObiRvalidM)        NextState = DONE;
      DONE:      if (ReadyW)            NextState = IDLE;
      default:   NextState = IDLE;
    endcase
  end

  // outputs
  assign ObiReqM  = (State == IDLE) & MemReqM;
  assign CaptureM = (State == WAIT_RESP) & ObiRvalidM;
  assign DoneM    = (State == DONE);

endmodule
