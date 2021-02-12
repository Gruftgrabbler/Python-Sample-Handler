"""
The sample handler is a multi purpose python script for reading, converting and writing audio samples to use with the
microcontroller based sample playback player. Its required to use this in combination with an audio tool like audacity
and the binary2header converter which is also included in the project.

    Preparation (Example):
    - Load up a sample in Audacity
    - Reduce the project rate down to 11025
    - Export Audio as raw header-less file with unsigned (important!) 8 or 16 bit encoding
    - Use the binary2header converter to create a C/C++ Header file from the raw binary

    Now all Preparation's are done. You can use the sample handler script to:
    - Just read and print/plot the data
    - Reduce the samplerate (even more) by specifying the ratio
    - Convert the sample encoding into twos complement encoding which is required for the i2s code to work
    - Automatic Header Writeback for continent usage with your code or the template TODO In Progress
    - Automatic Wavefile Writeback which enables you to compare the processed sample with the original one

    For example you can use the script like that:

        python sample_handler [path] [-r] [-plt] [-p] [-t]

    which reads the given file, reduces it samplerate by factor r and converts the data into twos complement
    representation and finally outputs the result on the terminal as well as a matplotlib plot.

    For example I converted the kick drum sample for the padauk pfs 173 with this command:

        python sample_handler ../samples/kick/kick.raw.h -r 2 -plt -c 1 -p  -t -w ../samples/kick/writeback2.wav -sr 5512

    which reads the kick drum header file, keeps it samplerate at the original 11025, cuts the last element from the
    list, converts it in twos complement representation, write the resulting audio back and finally prints the data to
    the terminal, as well as plots it via matplotlib.

    Future Improvements:
    - [ ] TODO Ability to read the wavefile directly (do this with soundfile as well)
    - [ ] TODO Add Header Writeback
    - [ ] TODO Implement Header Write back method for SDCC code
    - [ ] TODO Add Parameter Bit Depth to decide weather the twos complement representation uses 8 or 16 bit
"""
import numpy as np
import soundfile as sf


# ---------------------------------------------------------------------
# FILE READER MODULE
# ---------------------------------------------------------------------

class Filereader:
    """
    This module is an ease to use module to read header files converted from bin2header and wav2header converters
    """

    @staticmethod
    def read_file(file, startswith='static const'):
        """
        Reads a C/C++ File containing a single array and returns the C/C++ array as a python list.
        The input file can be formatted as hexadecimal or decimal and the output is always decimal
        :param file: path to given file
        :param startswith: AFTER the line which contains the startswith str the actual array begins
        :return: python list from C/C++ array
        """
        with open(file) as f:
            is_processing = False
            out = []
            for line in f:
                if line.startswith(startswith):
                    is_processing = True
                elif line.startswith('};'):
                    break
                elif is_processing:
                    out.extend(Filereader.__process_line(line))

            return out

    @staticmethod
    def __process_line(line):
        """
        Processes a single line of the array which contains str data and converts it to int
        :param line: line of the given array
        :return: array of int
        """
        line = line.strip()
        items = line.split(',')

        # Cut the last element if its an empty string, for example '\n'
        if not items[-1]:
            items = items[:-1]
        out = []
        # If encoding is hexadecimal
        if items[0].startswith('0x'):
            [out.append(int(item, 16)) for item in items]

        # If encoding is decimal
        elif items[0].startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9')):
            [out.append(int(item)) for item in items]
        return out


# ---------------------------------------------------------------------
# SAMPLE CONVERSION MODULE
# ---------------------------------------------------------------------

class Converter:

    @staticmethod
    def reduce_samplerate(sample_data, ratio):
        out = []
        sample_sum = 0.0

        for i in range(len(sample_data)):
            sample_sum += sample_data[i]
            if i % ratio == 0:
                out.append(int(sample_sum / ratio))
                sample_sum = 0
        return out

    @staticmethod
    def twos_complement(sample_data, max_value=0x7F):
        # TODO Add Bit Depth to parser which enables control over max_value
        out = []
        for i in range(len(sample_data)):
            current_sample = sample_data[i]
            twos_complement_value = current_sample - (max_value + 1) if current_sample > max_value else \
                abs(~current_sample) + max_value
            out.append(twos_complement_value)
        return out


# ---------------------------------------------------------------------
# SAMPLE WRITEBACK MODULE
# ---------------------------------------------------------------------

class Writeback:
    @staticmethod
    def write_header(file: str, declaration: str, data, style=None):
        """
        Writes a python list to a C/C++ header file
        :param file: Filename
        :param declaration: Declaration of array, for example:
            const uint8_t sample_data
            or:
            __code const uint8_t sample_data
        :param data:
        :param style: Will decide how if the array elements are fully embraced or not
            for style == 'SDCC' it will {number} embrace every element. Otherwise it does nothing
        :return: True if file was written successfully
        """
        with open(file, mode='w') as f:
            f.write('#ifndef SAMPLE_H\n'
                    '#define SAMPLE_H\n')
            f.write('const int SAMPLE_LEN = {};\n'.format(len(data)))
            f.write(declaration)
            f.write('= {\n')
            if type == 'SDCC':
                pass  # TODO Implement SDCC Write Header
            else:
                f.write(data)
            f.write('\n};\n'
                    '#endif\n')

    @staticmethod
    def write_wavefile(sample_data, path: str, samplerate: int, bits=8):
        sample_data_np = np.array(sample_data, dtype='int16')
        sample_data_np = sample_data_np << (16 - bits)
        sf.write(path, sample_data_np, samplerate)


if __name__ == '__main__':
    import argparse
    import matplotlib.pyplot as plt

    # -----------------------------------------------------------------
    # ARGUMENT PARSING
    # -----------------------------------------------------------------

    parser = argparse.ArgumentParser()

    # General Arguments
    parser.add_argument('-p', action='store_true',
                        help='Print the resulting data to the command line')
    parser.add_argument('-plt', action='store_true',
                        help='Plot the resulting data with matplotlib.pyplot')

    # Filereader Arguments
    parser_group_filereader = parser.add_argument_group('Filereader')
    parser_group_filereader.add_argument('path', type=str,
                                         help='Path to file')
    parser_group_filereader.add_argument('-dec',
                                         help='Declaration line of the array. for example:\n'
                                              'static const uint_8 array',
                                         default='static const')
    parser_group_filereader.add_argument('-cut', type=int,
                                         help='If specified: Cut samples from the end of the loaded array')

    # Sample Conversion Arguments
    parser_group_conversion = parser.add_argument_group('Sample Conversion')
    parser_group_conversion.add_argument('-r', '--ratio', type=int,
                                         help='Ratio of Samplerate reduction')
    parser_group_conversion.add_argument('-t', action='store_true',
                                         help='Activate twos complement conversion on the data')
    # Sample Writeback Arguments
    parser_group_writeback = parser.add_argument_group('Sample Writeback')
    parser_group_writeback.add_argument('-wb', metavar='writeback', type=str,
                                        help='If specified: Name of wav File where data is written back to ')
    parser_group_writeback.add_argument('-sr', metavar='samplerate', type=int,
                                        help='Specify writeback samplerate')

    # If writeback is specified a samplerate must be specified as well!
    args = parser.parse_args()
    if ('wb' in vars(args)) and 'sr' not in vars(args):
        parser.error('Sample Writeback requires a samplerate specification')

    # -----------------------------------------------------------------
    # PROGRAM EXECUTION
    # -----------------------------------------------------------------

    # Read File
    sample = Filereader.read_file(args.path, startswith=args.dec)

    if args.cut:
        sample = sample[:-args.cut]

    # Convert Samplerate
    if args.ratio:
        sample = Converter.reduce_samplerate(sample, args.ratio)

    # Convert the sample into twos complement representation
    if args.t:
        sample = Converter.twos_complement(sample)

    # Print the sample to the terminal
    if args.p:
        print('Processed sample data:\n {} \n Sample Length: {}\n'.format(sample, len(sample)))

    # Write Header
    # TODO Add Parser Argument for Header Write back

    # Write Wavefile
    # Note: We need to convert the data into non twos complement representation again by calling
    # the twos complement converter once again
    # TODO Add Bit Parameter to Writeback
    if args.wb:
        Writeback.write_wavefile(Converter.twos_complement(sample), args.wb, args.sr)

    # Plot the sample using matplotlib.pyplot
    if args.plt:
        plt.plot(sample)
        plt.show()
