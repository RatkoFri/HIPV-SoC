// Simple dual-port synchronous RAM (one read port, one write port),
// 1-cycle read latency. Not used by the SoC (the unified memory needs
// true dual-port); kept as a teaching primitive.
//
// Fixes vs the original upload: parameter list moved after the module
// name, port-list commas corrected, `data_out`/`data_reg` naming
// mismatch resolved, `inital` -> `initial`, INIT_FILE parameter.

module sync_simple_dual_port_RAM #(
    parameter DATA_WIDTH = 8,
    parameter ADDR_WIDTH = 8,
    parameter INIT_FILE  = ""
) (
    input logic clock,
    // Read Port
    input logic [ADDR_WIDTH-1:0] addr_r,
    output logic [DATA_WIDTH-1:0] dataout,
    // Write Port
    input logic [ADDR_WIDTH-1:0] addr_w,
    input logic [DATA_WIDTH-1:0] datain,
    input logic we
);

    logic [DATA_WIDTH-1:0] mem [0:2**ADDR_WIDTH-1];
    logic [DATA_WIDTH-1:0] data_reg;

    always_ff @(posedge clock) begin
        if (we) begin
            mem[addr_w] <= datain;
        end
        data_reg <= mem[addr_r];
    end

    assign dataout = data_reg;

    initial begin
        if (INIT_FILE != "") $readmemh(INIT_FILE, mem);
    end

endmodule
