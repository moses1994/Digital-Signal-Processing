from scipy.fftpack import fft,ifft
from scipy.io.wavfile import read,write
from scipy.signal import get_window
import numpy as np
from pdb import set_trace

class Signal:

    def __init__(self,filename):
        self.rate, self.data = read(filename)
        self.dtype = self.data.dtype
    
    def write(self,filename):
        write(filename,self.rate,self.data)

    # def copy(self):
    #     np.copy(self.data)
    def amplify(self,gain):
        self.data *= gain

    def moving_average_filter(self,N=5):
        x = self.data
        N = max(2,N)
        N = min(len(x),N)
        y = []
        cum = float(sum(x[0:N]))
        for i in range(len(x)):
            y.append(cum/N)
            cum -= x[i]
            cum += x[(i+N)%len(x)]
        self.data = np.array(y,x.dtype)

    def noise_removal(self,noise):
        fft_size = 2049
        hann_win = get_window('hann',fft_size)
        band_width = 17
        triang_bank = get_window('triang',band_width)
        freq_step = (band_width-1)/2
        freq_supp_size = (fft_size-1)/2+1

        # freq_pad_size = (freq_supp_size-band_width)%freq_step
        freq_pad_size = freq_step-freq_supp_size%freq_step+1
        num_bands = (freq_supp_size-band_width+freq_pad_size)/freq_step+1
        # num_bands = (freq_supp_size-band_width)/freq_step+1
        # freq_pad_size = band_width+freq_step*(num_bands-1)-freq_supp_size
        num_bands += 2
        
        # Get threshold for each frequency band
        noise_spectrum = fft(noise.data,fft_size)[0:freq_supp_size]
        zeros = np.zeros(freq_pad_size,dtype=np.complex)
        noise_spectrum = np.hstack((noise_spectrum,zeros))
        zeros = np.zeros(freq_step,dtype=np.complex)
        noise_spectrum = np.hstack((zeros,noise_spectrum,zeros))
        thresholds = []
        for i in range(num_bands):
            start = i*freq_step
            band = noise_spectrum[start:start+band_width]*triang_bank
            energy = sum(map(lambda x:np.power(np.abs(x),2),band))
            thresholds.append(energy)
            # set_trace()

        # Pad the original signal to its end
        time_step = (fft_size-1)/2
        pad_size = time_step-len(self.data)%time_step+1
        num_frames = (len(self.data)-fft_size+pad_size)/time_step+1
        # num_frames = (len(self.data)-fft_size)/time_step+1
        # pad_size = time_step*(num_frames-1)+fft_size-len(self.data)
        zeros = np.zeros(pad_size,self.dtype)
        data = np.hstack((self.data,zeros))

        # Pad 2 sides of the original signal with zeros
        zeros = np.zeros(time_step,self.dtype)
        data = np.hstack((zeros,data,zeros))
        num_frames += 2

        # Frame signal
        frames = []
        for i in range(num_frames):
            start = i*time_step
            frame = data[start:start+fft_size]*hann_win
            frames.append(frame)
        

        # Spectral analysis
        sharpness = 0.01
        new_frames = []
        for frame in frames:
            spectrum = fft(frame)[0:freq_supp_size]
            zeros = np.zeros(freq_pad_size,dtype=np.complex)
            spectrum = np.hstack((spectrum,zeros))
            zeros = np.zeros(freq_step,dtype=np.complex)
            spectrum = np.hstack((zeros,spectrum,zeros))
            
            bands = []
            for i in range(num_bands):
                start = i*freq_step
                band = spectrum[start:start+band_width]*triang_bank
                energy = sum(map(lambda x:np.power(np.abs(x),2),band))
                diff = energy-thresholds[i]
                gain = 1.0/(1+np.exp(-sharpness*diff))
                band *= gain    # Attenuate
                bands.append(band)
            # Retrieve attenuated spectrum
            new_spectrum = np.zeros(freq_supp_size,dtype=np.complex)
            for i in range(freq_supp_size-1):
                # set_trace()
                band_1 = bands[i/freq_step]
                band_2 = bands[i/freq_step+1]
                new_spectrum[i] = band_1[freq_step+i%freq_step]+band_2[i%freq_step]
            new_spectrum[freq_supp_size-1] = bands[(freq_supp_size-1)/freq_step][freq_step]
            new_spectrum = np.hstack((new_spectrum,new_spectrum[::-1][0:freq_supp_size-1]))
            # Retrieve attenuated frame
            new_frame = np.real(ifft(new_spectrum))
            new_frames.append(new_frame)
        # Retrieve attenuated signal
        new_data = np.zeros(len(self.data))
        for i in range(len(self.data)-1):
            # set_trace()
            frame_1 = new_frames[i/time_step]
            frame_2 = new_frames[i/time_step+1]
            new_data[i] = frame_1[time_step+i%time_step]+frame_2[i%time_step]
        new_data[len(self.data)-1] = new_frames[(len(self.data)-1)/time_step][time_step]
        self.data = np.array(new_data,dtype=self.dtype)

            


