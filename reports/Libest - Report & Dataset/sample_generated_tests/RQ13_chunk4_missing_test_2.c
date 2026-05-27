/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk4_missing_test_2.c
 */

#include <string.h>

static void rq13_chunk4_missing_test_2 (void)
{
    long rv_https;
    long rv_plain;
    char plain_url[512];

    LOG_FUNC_NM
    ;

    /* Perform the enroll over the HTTPS endpoint and assert HTTP success */
    rv_https = curl_http_post(US893_REENROLL_URL_BA, US893_PKCS10_CT,
        US893_PKCS10_RSA2048,
        US893_UIDPWD_GOOD, US893_CACERTS, CURLAUTH_BASIC, NULL, NULL, NULL);
    /* Expect the reenroll to succeed when transported over TLS */
    CU_ASSERT(rv_https == 200);

    /*
     * Construct a plain HTTP URL by removing the 's' from the "https://"
     * prefix of the existing constant.  This mirrors the same enroll
     * request but over an unencrypted transport to validate rejection.
     */
    strncpy(plain_url, US893_REENROLL_URL_BA, sizeof(plain_url) - 1);
    plain_url[sizeof(plain_url) - 1] = '\0';
    if (strncmp(plain_url, "https://", 8) == 0) {
        /* remove the 's' to form "http://" */
        memmove(plain_url + 4, plain_url + 5, strlen(plain_url + 5) + 1);
    }

    /* Attempt the same enroll over plain HTTP */
    rv_plain = curl_http_post(plain_url, US893_PKCS10_CT,
        US893_PKCS10_RSA2048,
        US893_UIDPWD_GOOD, US893_CACERTS, CURLAUTH_BASIC, NULL, NULL, NULL);

    /* The plain HTTP transport should not be accepted for enrollment (not 200). */
    CU_ASSERT(rv_plain != 200);
}
