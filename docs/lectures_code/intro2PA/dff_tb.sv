`timescale 1ns/1ps

`include "dff.sv"

module dff_tb ();
    
    // Inputs
    logic clk;
    logic rst;
    logic D;

    // Outputs
    logic Q;

    // Instantiate the Unit Under Test (UUT)
    dff uut (
        .clk(clk), 
        .rst(rst),
        .D(D), 
        .Q(Q)
    );

    // Clock generation
    initial begin
        clk = 0;
        forever begin
            #5;
            clk = ~ clk;
        end
    end

    initial begin
        $dumpfile("dff_tb.vcd");
        $dumpvars;

        // Initialize Inputs
        rst = 1; // Assert reset
        D = 0;
        #10;     // Wait for 10 time units

        rst = 0; // Deassert reset
        D = 1;
        #10;     // Wait for 10 time units

        D = 0;
        #10;     // Wait for 10 time units

        D = 1;
        #10;     // Wait for 10 time units

        rst = 1; // Assert reset again
        #10;     // Wait for 10 time units

        $display("Test completed. The simulation lasted for %t time units.", $time);
        $finish; // End simulation
    end

endmodule
