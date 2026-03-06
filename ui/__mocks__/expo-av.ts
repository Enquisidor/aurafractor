const soundMock = {
  loadAsync: jest.fn().mockResolvedValue({}),
  unloadAsync: jest.fn().mockResolvedValue({}),
  playAsync: jest.fn().mockResolvedValue({}),
  pauseAsync: jest.fn().mockResolvedValue({}),
  setPositionAsync: jest.fn().mockResolvedValue({}),
  setOnPlaybackStatusUpdate: jest.fn(),
  getStatusAsync: jest.fn().mockResolvedValue({ isLoaded: false }),
};

export const Audio = {
  Sound: {
    createAsync: jest.fn().mockResolvedValue({
      sound: soundMock,
      status: { isLoaded: true, durationMillis: 60000, positionMillis: 0 },
    }),
  },
  setAudioModeAsync: jest.fn().mockResolvedValue({}),
};
