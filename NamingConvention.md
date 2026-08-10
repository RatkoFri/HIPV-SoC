## Naming convention for HIPV (HIP RISCV SOC)

1. Use flatcase for clk and reset signals. 

2. Use UpperCamelCase for signals

3. Use MACRO_CASE for constants and parameters.

4. Use suffixes on all singals associated with pipeline stages. For HIPV, the suffixes are as follows:
   - `F` for signals in the Fetch stage
   - `D` for signals in the Decode stage
   - `E` for signals in the Execute stage
   - `M` for signals in the Memory stage
   - `W` for signals in the Writeback stage

5. Use prefixes to distinguish between different sources:
    - Distinguish between similar signals from different sources:
      - `IEUResultM` for the result from the IEU in the Memory stage
      - `ALUResultM` for the result from the ALU in the Memory stage

6.  Declaring signals:
    - declare all signals 
    - bidirectional signals are only used on top-level modules and should be avoided in sub-modules. Use separate input and output signals instead.
    - delclare signals as `logic` type instead of `wire` type. Use `wire` type only for combinational logic that is not registered.
    - declare busses as little-endian, with the least significant bit on the right. For example, a 32-bit bus should be declared as `[31:0]`.
    - do not use arrays of signals as ports. 

7. Port connection
   - connect ports by name for other modules.
      ```verilog 
      .portName(signalName)
      ``` 
    - avoid .* notation 

8. SPacing and indentation
   - indent with spaces instead of tabs. 
   - use 2 spaces for each level of indentation.
   - align signal declaration within a block
   - leave a space around operators and after if/case/for statements.
   - avoid space before semicolon, commas, open and close parentheses, in module instantation and inside bus width declaration.
   - only use `begin` and `end` for multi-line blocks. For single line blocks, use the statement without `begin` and `end`.
   - pack the `begin` statement and the first statement of the block on the same line. 
   - Limit lines to 95 characters. If a line exceeds 95 characters, break it into multiple lines and indent the continuation lines by 2 spaces.
   - use blank lines sparingly to separate logical blocks of code, but avoid excessive blank lines.
   - use banner comments sparingly to separate logical blocks of code, but avoid excessive banner comments.

9. Synchronous design
    - use synchronous sequential design.
    - instantiate memories and flip-flops with synchronous reset and enable signals.
    - do not use # delays in RTL code, except for testbenches.

10. Modules 
    - Place eache module in a separate file, with the file name matching the module name.
    - The module name is immediately followed by the `(` with bi soacem and the inbput and output ports begin on same line as the module name, when the module is not parameterized. 
    - For parameterized modules, place the parameters on same a line as a module declaration. Place input and output ports on subsequent lines, with each port on a separate line and indented by 2 spaces.. Place the closing `)` on a same line as last port declaration, with no space before the `)`.
    - One input or output keyword is on each line of in the module declaration, and pots with the same direction and width are declared on the same line, separated by commas. Text is aligned horizontally for each port declaration, with the port name aligned to the right of the direction and width.
    - use behavioral coding style for leaf cells, including generic blocks and control blocks. 
    - use structural coding style for dataflow as much as possible, including datapath and memory blocks.
    - use hiearchy so that modules remain small and easy to understand. 
    - avoid programming constructs that obscure the hardware being implied.

11. Configurable hardware 
    - define generic configurable blocks where appropriate
    - use a parameter structure to pass parameters to the top level and its sub-modules.
    - use `#parameter` to define parameters in modules, and use `localparam` for internal constants that should not be modified externally.
    - module interfaces should remain wheter or not feature is enabled
      - unused ports should be tied off to a default value, such as 0 or 1, when the feature is disabled.
    - when a generate block contains instance of signal declarations, name the block with a colon after the block name, and use the block name as a prefix for the instance names. For example:
      ```verilog
      generate
        if (FEATURE_ENABLED) begin : feature_block
          my_module feature_instance (
            .clk(clk),
            .reset(reset),
            .input_signal(input_signal),
            .output_signal(output_signal)
          );
        end
      endgenerate
      ```
12. Comments
    - uplace a banner comment at the top of each file, describing the module's purpose, author, and date.
    - use comments to explain the purpose and functionality of complex code sections, especially for non-obvious logic or algorithms.
    - use block comments for multi-line explanations and single-line comments for brief notes.
    - keep comments up-to-date with code changes to maintain accuracy.