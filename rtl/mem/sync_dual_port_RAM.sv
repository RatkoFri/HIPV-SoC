// True dual-port synchronous RAM (two independent read/write ports).
// 1-cycle read latency on both ports; each port is read-first on a
// same-port write. Maps onto FPGA BRAM true-dual-port mode.
//
// INIT_FILE: $readmemh image applied at elaboration (synthesis-time
// initialization — Vivado folds it into the bitstream); empty string
// leaves the array uninitialized.
//
// Behaviour is undefined when both ports write the same address in the
// same cycle (as in real BRAM); the simulation model lets port B win.
//
// Fixes vs the original upload: parameter list moved after the module
// name, `inital` -> `initial`, hard-coded "mem_init.txt" replaced by
// the INIT_FILE parameter.

module sync_dual_port_RAM #(
    parameter DATA_WIDTH = 8,
    parameter ADDR_WIDTH = 8,
    parameter INIT_FILE  = ""
) (
    input logic clock,
    input logic [ADDR_WIDTH-1:0] addr_a,
    input logic [ADDR_WIDTH-1:0] addr_b,
    input logic [DATA_WIDTH-1:0] datain_a,
    input logic [DATA_WIDTH-1:0] datain_b,
    input logic we_a,
    input logic we_b,
    output logic [DATA_WIDTH-1:0] dataout_a,
    output logic [DATA_WIDTH-1:0] dataout_b
);

    logic [DATA_WIDTH-1:0] mem [0:2**ADDR_WIDTH-1];
    logic [DATA_WIDTH-1:0] data_a, data_b;

    always_ff @(posedge clock) begin
        if (we_a) begin
            mem[addr_a] <= datain_a;
        end
        data_a <= mem[addr_a];
    end

    always_ff @(posedge clock) begin
        if (we_b) begin
            mem[addr_b] <= datain_b;
        end
        data_b <= mem[addr_b];
    end

    assign dataout_a = data_a;
    assign dataout_b = data_b;

    initial begin
        if (INIT_FILE != "") $readmemh(INIT_FILE, mem);
    end

endmodule
