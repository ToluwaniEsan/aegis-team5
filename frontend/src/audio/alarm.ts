import { ALARM_FREQUENCIES_HZ, ALARM_TONE_SECONDS } from "../config";

export class Alarm {
  private context: AudioContext | null = null;
  private oscillators = new Set<OscillatorNode>();

  async unlock(): Promise<void> {
    this.context ??= new AudioContext();
    await this.context.resume();
    if (this.context.state !== "running") throw new Error("Audio unavailable");
  }

  play(): void {
    if (!this.context || this.context.state !== "running")
      throw new Error("Audio unavailable");
    const context = this.context;
    ALARM_FREQUENCIES_HZ.forEach((frequency, index) => {
      const oscillator = context.createOscillator();
      this.oscillators.add(oscillator);
      oscillator.frequency.value = frequency;
      oscillator.connect(context.destination);
      const start = context.currentTime + index * ALARM_TONE_SECONDS;
      oscillator.start(start);
      oscillator.stop(start + ALARM_TONE_SECONDS);
      oscillator.onended = () => {
        oscillator.disconnect();
        this.oscillators.delete(oscillator);
      };
    });
  }

  stop(): void {
    for (const oscillator of this.oscillators) {
      oscillator.onended = null;
      try {
        oscillator.stop();
      } catch {
        /* Already stopped. */
      }
      oscillator.disconnect();
    }
    this.oscillators.clear();
  }

  async close(): Promise<void> {
    const context = this.context;
    this.stop();
    this.context = null;
    if (context) await context.close();
  }
}
