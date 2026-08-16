///////////////////////////////////////////////////////////////////////
// obi_arbiter
//
// Purpose: Request arbiter for one crossbar slave port. Selects one
//          requesting master and drives a one-hot grant.
//          ARB_POLICY selects the policy:
//            ARB_FIXED       - lowest master index always wins
//            ARB_ROUND_ROBIN - rotating priority, advanced by Update
//          Update should be asserted in the cycle a grant is actually
//          taken, so the pointer only moves on real transfers.
//          The round-robin pointer is the only state; with ARB_FIXED
//          the module is purely combinational.
// Author:  Ratko Pilipovic
// Date:    12 August 2026
///////////////////////////////////////////////////////////////////////

// The port list is the same for both policies (coding standard: module
// interfaces stay constant whether or not a feature is enabled), so
// clk/reset/Update are legitimately unused when ARB_POLICY = ARB_FIXED.
/* verilator lint_off UNUSEDSIGNAL */
module obi_arbiter #(parameter NUM_MASTERS = 2,
                     parameter ARB_POLICY  = 0) (
  input  logic                   clk, reset,
  input  logic [NUM_MASTERS-1:0] Req,
  input  logic                   Update,
  output logic [NUM_MASTERS-1:0] Grant);
/* verilator lint_on UNUSEDSIGNAL */

  localparam int unsigned PTR_W = (NUM_MASTERS > 1) ? $clog2(NUM_MASTERS) : 1;

  // lowest set bit of Req, as a one-hot vector
  function automatic logic [NUM_MASTERS-1:0] lowest_set(
      input logic [NUM_MASTERS-1:0] R);
    logic [NUM_MASTERS-1:0] Y;
    Y = '0;
    for (int i = NUM_MASTERS - 1; i >= 0; i--)
      if (R[i]) Y = (1 << i);
    return Y;
  endfunction

  generate
    if (ARB_POLICY == 0) begin : gen_fixed

      assign Grant = lowest_set(Req);

    end else begin : gen_round_robin

      logic [PTR_W-1:0]       Ptr;
      logic [NUM_MASTERS-1:0] Masked, GrantMasked;

      // masters at or above the pointer have priority this round
      always_comb begin
        Masked = '0;
        for (int i = 0; i < NUM_MASTERS; i++)
          if (i >= int'(Ptr)) Masked[i] = Req[i];
      end

      assign GrantMasked = lowest_set(Masked);
      // if nobody at or above the pointer asked, wrap around
      assign Grant = (|Masked) ? GrantMasked : lowest_set(Req);

      // advance past the master just served
      always_ff @(posedge clk)
        if (reset) Ptr <= '0;
        else if (Update & |Grant) begin
          Ptr <= '0;
          for (int i = 0; i < NUM_MASTERS; i++)
            if (Grant[i])
              Ptr <= (i == NUM_MASTERS - 1) ? '0 : PTR_W'(i + 1);
        end

    end
  endgenerate

endmodule
