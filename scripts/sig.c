#include <string.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <linux/wireless.h>
#include <stdio.h>

int main(void)
{
  struct iwreq iwr;
  struct iw_statistics stat;

  int sk = socket(AF_INET, SOCK_DGRAM, 0);

  memset(&iwr, 0, sizeof(iwr));
  memset(&stat, 0, sizeof(stat));
  strncpy(iwr.ifr_name, "wlan0", IFNAMSIZ);
  iwr.u.data.pointer = &stat;
  iwr.u.data.length = sizeof(stat);

  ioctl(sk, SIOCGIWSTATS, &iwr);
  close(sk);

  printf("link quality: %d\n", stat.qual.qual);
  if(stat.qual.updated & IW_QUAL_DBM) {
    printf("link level %d dBm\n", (char)stat.qual.level);
    printf("noise %d dBm\n", (char)stat.qual.noise);
  } else {
    printf("link level %d\n", (char)stat.qual.level);
    printf("noise %d\n", (char)stat.qual.noise);
  }

  return 0;
}
