// 1. set timescale 
`timescale 1ns/1ps

// 2. include DUT file ` 
`include "mux4to1.sv"
// 3. declare module for testbench
module mux4to1_tb ();
    
    // 4. instantiate source and sink signals
    logic [3:0] I_tb; // source 
    logic [1:0] S_tb; // source
    logic O_tb; // sink

    // 5. instantiate the Unit Under Test (UUT)
    mux4to1 uut(
        .I(I_tb),
        .S(S_tb),
        .O(O_tb)
    );
    // 6. create initial block for stimulus
    initial begin
        $dumpfile("tb.vcd"); 
        $dumpvars;
        // I = 4'b1010; S = 2'b00; for 10 time units then change S to 2'b01 for 10 time units etc.
        I_tb = 4'b1010; 
        S_tb = 2'b00;
        #10 // delaz for 10 time units 
        S_tb = 2'b01;
        #10 
        S_tb = 2'b10;
        #10
        S_tb = 2'b1ß1;
        #10 
        // 7. display message and finish simulation
        $display("Test completed. The simulation lasted for %t time units.", $time);
        $finish;
    end


// 8. dump waveform file       $dumpfile("tb.vcd"); $dumpvars;

endmodule

