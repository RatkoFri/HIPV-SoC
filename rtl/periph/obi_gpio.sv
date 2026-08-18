module obi_gpio #(
    parameter int unsigned ADDR_WIDTH = 32,
    parameter int unsigned DATA_WIDTH = 32,
    parameter int unsigned NUM_IN = 8,
    parameter int unsigned NUM_OUT = 8
) (
    input logic clk_i,
    input logic rstn_i,

    input   logic                     obi_areq_i,
    output  logic                     obi_agnt_o,
    input   logic [ADDR_WIDTH-1:0]    obi_aaddr_i,
    input   logic [DATA_WIDTH-1:0]    obi_awdata_i,

    input   logic                     obi_awe_i,
    input   logic [DATA_WIDTH/8-1:0]  obi_abe_i,

    output  logic                     obi_rvalid_o,
    input   logic                     obi_rready_i,
    output  logic [DATA_WIDTH-1:0]    obi_rdata_o,
    output  logic                     obi_rerr_o,   // Response Error - TODO

    input   logic [NUM_IN-1:0]       gpio_in_i,
    output  logic [NUM_OUT-1:0]      gpio_out_o
);
    
    localparam int unsigned GpoRegOffset = 0;
    localparam int unsigned GpiRegOffset = 4; 

    logic [NUM_IN-1:0]  gpio_in;

    
    logic [DATA_WIDTH-1:0] obi_read_data;

    // OBI wrapper signals
    typedef enum logic {
        ADDR,
        RESP
    } state_t;
    state_t state, next_state;

    logic obi_a_fire;
    logic obi_r_fire;
    logic capture;


    // Write interface signals
    logic wr_en;
    logic [DATA_WIDTH-1:0] write_data_mask;


    // Read interface signals
    logic rd_en;
    logic [DATA_WIDTH-1:0] read_data_mux;


    // BEGIN: OBI wrapper
    register  #(
        .DTYPE(state_t),
        .RESET_VALUE(ADDR)     
    ) obi_fsm_state_reg
        (
        .clk(clk_i),
        .rstn(rstn_i),
        .ce(1'b1), // Always enable to capture the input state
        .in(next_state),
        .out(state)
    );

    assign obi_a_fire = obi_areq_i && obi_agnt_o;
    assign obi_r_fire = obi_rready_i && obi_rvalid_o;

    // State transition logic
    always_comb begin : OBI_SLAVE_next_state
        next_state = state;
        case (state)
            ADDR: begin
                if (obi_a_fire) begin // handshake for address phase, when there is a valid request and the slave is granted access to the bus, move to response phase
                    next_state = RESP;
                end
            end
            RESP: begin
                if (obi_r_fire) begin // handshake for response phase, when there is a valid response and the master is ready to accept it, move back to address phase
                    next_state = ADDR;
                end
            end
        endcase
    end

    assign obi_agnt_o = (state == ADDR); // Grant access to the bus during address phase
    assign obi_rvalid_o = (state == RESP); // Grant access to the bus during response phase

    // END: OBI wrapper

    // BEGIN: OBI write interface
    
    assign wr_en = obi_a_fire & obi_awe_i & (obi_aaddr_i[6:0] == GpoRegOffset); // Needs to ensure write request is valid and handshake occured in address phase

    assign write_data_mask = {{8{obi_abe_i[3]}},{8{obi_abe_i[2]}},{8{obi_abe_i[1]}},{8{obi_abe_i[0]}}}; 


    register  #(
        .DTYPE(logic [NUM_OUT-1:0]),
        .RESET_VALUE('0)     
    ) gpo_reg
        (
        .clk(clk_i),
        .rstn(rstn_i),
        .ce(wr_en),
        .in(obi_awdata_i[NUM_OUT-1:0] & write_data_mask[NUM_OUT-1:0]),
        .out(gpio_out_o)
    );

    // END: OBI write interface

    // BEGIN: OBI read interface
    assign rd_en = obi_a_fire & !obi_awe_i ; 

    register  #(
        .DTYPE(logic [NUM_IN-1:0]),
        .RESET_VALUE('0)     
    ) gpi_reg
        (
        .clk(clk_i),
        .rstn(rstn_i),
        .ce(1'b1), // Always enable to capture the input state
        .in(gpio_in_i),
        .out(gpio_in)
    );


    always_comb begin 
        read_data_mux = '0; // Default to zero
        if(rd_en) begin
            case(obi_aaddr_i[6:0])
                GpoRegOffset: read_data_mux = {{(DATA_WIDTH-NUM_OUT){1'b0}}, gpio_out_o}; // Zero-extend GPO
                GpiRegOffset: read_data_mux = {{(DATA_WIDTH-NUM_IN){1'b0}}, gpio_in};  // Zero-extend GPI
                default: read_data_mux = '0; // Default to zero for unmapped addresses
            endcase
        end
    end

    // register to hold the read data during response phase, so that it can be output when rvalid is high
    register  #(
        .DTYPE(logic [DATA_WIDTH-1:0]),
        .RESET_VALUE('0)     
    ) obi_read_data_reg
        (
        .clk(clk_i),
        .rstn(rstn_i),
        .ce(obi_a_fire), // Capture read data when read enable is high
        .in(read_data_mux),
        .out(obi_rdata_o)
    );

    // END: logic for OBI read interface

    // error handling logic
    always_comb begin 
        obi_rerr_o = 1'b0; // Default to no error
        if (state == RESP) begin // Only check for read errors during response phase for read transactions
            case(obi_aaddr_i[6:0])
                GpoRegOffset, GpiRegOffset: obi_rerr_o = 1'b0; // Valid addresses
                default: obi_rerr_o = 1'b1; // Invalid address
            endcase
        end
    end

endmodule

// -----------------------------------------------------------------------------
// obi_gpio instantiation template
// -----------------------------------------------------------------------------
// obi_gpio #(
//     .ADDR_WIDTH(32),
//     .DATA_WIDTH(32),
//     .NUM_IN(8),
//     .NUM_OUT(8)
// ) u_obi_gpio (
//     .clk_i       (clk_i),
//     .rstn_i      (rstn_i),
//     .obi_areq_i  (obi_areq_i),
//     .obi_agnt_o  (obi_agnt_o),
//     .obi_aaddr_i (obi_aaddr_i),
//     .obi_awdata_i(obi_awdata_i),
//     .obi_awe_i   (obi_awe_i),
//     .obi_abe_i   (obi_abe_i),
//     .obi_rvalid_o(obi_rvalid_o),
//     .obi_rready_i(obi_rready_i),
//     .obi_rdata_o (obi_rdata_o),
//     .obi_rerr_o  (obi_rerr_o),
//     .gpio_in_i   (gpio_in_i),
//     .gpio_out_o  (gpio_out_o)
// );
