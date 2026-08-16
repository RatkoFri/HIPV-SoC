///////////////////////////////////////////////////////////////////////
// obi_decoder
//
// Purpose: Address decoder for the HIPV SoC crossbar. Maps a master
//          address to a one-hot slave select using the address map in
//          hipv_soc_pkg. DecErr is asserted when the address falls
//          outside every mapped region; the crossbar then answers the
//          access from its internal error responder instead of
//          hanging the bus.
//          Purely combinational, one instance per master port.
// Author:  Ratko Pilipovic
// Date:    12 August 2026
///////////////////////////////////////////////////////////////////////

// The package import sits in the header so the port width can follow
// NUM_SLAVES: adding a slave to hipv_soc_pkg resizes SlaveSel here and
// in the crossbar automatically.
module obi_decoder
  import hipv_soc_pkg::*;
  (input  logic [31:0]           Addr,
   output logic [NUM_SLAVES-1:0] SlaveSel,
   output logic                  DecErr);

  // A region is matched by comparing the address bits above the region
  // size, which is why regions must be power-of-two sized and aligned.
  function automatic logic in_region(input logic [31:0] A,
                                     input logic [31:0] Base,
                                     input logic [31:0] Size);
    return (A & ~(Size - 32'd1)) == Base;
  endfunction

  always_comb begin
    SlaveSel = '0;
    SlaveSel[SLAVE_IMEM]  = in_region(Addr, IMEM_BASE, IMEM_SIZE);
    SlaveSel[SLAVE_DMEM]  = in_region(Addr, DMEM_BASE, DMEM_SIZE);
    SlaveSel[SLAVE_UART]  = in_region(Addr, UART_BASE, UART_SIZE);
    SlaveSel[SLAVE_TIMER] = in_region(Addr, TIMER_BASE, TIMER_SIZE);
    SlaveSel[SLAVE_GPIO]  = in_region(Addr, GPIO_BASE, GPIO_SIZE);
  end

  assign DecErr = ~|SlaveSel;

endmodule
