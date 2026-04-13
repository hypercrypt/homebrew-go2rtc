class Go2rtc < Formula
  desc "Camera streaming application with RTSP, WebRTC, HomeKit and FFmpeg support"
  homepage "https://github.com/AlexxIT/go2rtc"
  version "1.9.14"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/AlexxIT/go2rtc/releases/download/v1.9.14/go2rtc_mac_arm64.zip"
      sha256 "919b78adc759d6b3883d1e1b2ac915ac0985bb903ff1897b4d228527bd64690c"
    end
    on_intel do
      url "https://github.com/AlexxIT/go2rtc/releases/download/v1.9.14/go2rtc_mac_amd64.zip"
      sha256 "9b0b9a27a4dc3a5b8b93376e7e8fc2787c6af624a512842622be84aec0171c7a"
    end
  end

  def install
    bin.install "go2rtc"
  end

  test do
    system bin/"go2rtc", "-version"
  end
end
