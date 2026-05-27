/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk4_missing_test_1.c
 */

#include <stdio.h>
#include <string.h>
#include <CUnit/CUnit.h>

/*
 * Shared prelude: standard headers and CUnit include required by tests.
 * The project provides helpers such as curl_http_post and macros like
 * LOG_FUNC_NM and constants (US748_ENROLL_URL_BA, etc.) used below.
 */

static void rq13_chunk4_missing_test_1 (void)
{
    long rv;
    char plain_url[512];

    LOG_FUNC_NM
    ;

    /*
     * First, perform the normal enroll over the configured HTTPS URL
     * and assert the HTTP-level success as other tests do.  This
     * confirms the HTTP-layer operation when TLS transport is used.
     */
    rv = curl_http_post(US748_ENROLL_URL_BA, US748_PKCS10_CT,
                        US748_PKCS10_RSA2048,
                        US748_UIDPWD_GOOD, US748_CACERTS, CURLAUTH_BASIC, NULL, NULL, NULL);
    CU_ASSERT(rv == 200);

    /*
     * Now construct a plain HTTP URL by replacing the "https://"
     * scheme with "http://" and attempt the same enroll.  The
     * server should not accept the enrollment over plain HTTP; the
     * expected HTTP success (200) must not occur when TLS is absent.
     */
    if (strncmp(US748_ENROLL_URL_BA, "https://", 8) == 0) {
        /* skip the "https://" prefix and prefix with "http://" */
        snprintf(plain_url, sizeof(plain_url), "http://%s", US748_ENROLL_URL_BA + 8);
    } else {
        /* if the configured URL does not start with https, just prefix http:// */
        snprintf(plain_url, sizeof(plain_url), "http://%s", US748_ENROLL_URL_BA);
    }

    rv = curl_http_post(plain_url, US748_PKCS10_CT,
                        US748_PKCS10_RSA2048,
                        US748_UIDPWD_GOOD, US748_CACERTS, CURLAUTH_BASIC, NULL, NULL, NULL);

    /*
     * The plain-HTTP attempt must not succeed with the same HTTP 200
     * result observed over HTTPS.  We assert inequality to capture
     * rejection or failure modes when TLS is not used.
     */
    CU_ASSERT(rv != 200);
}
