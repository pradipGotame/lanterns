/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk4_missing_test_3.c
 */

#include <CUnit/CUnit.h>
#include <string.h>
#include <stdio.h>

/* This test uses existing test helpers and constants (e.g., curl_http_post,
 * US748_ENROLL_URL_BA, US748_PKCS10_CT, US748_PKCS10_RSA2048,
 * US748_UIDPWD_GOOD, US748_CACERTS, CURLAUTH_BASIC) which are provided by
 * the project's test harness and exemplars. */

static void rq13_chunk4_missing_test_3(void)
{
    long rv;
    char http_url[1024];
    const char *https_url = US748_ENROLL_URL_BA;

    LOG_FUNC_NM
    ;

    /*
     * Verify enrollment over HTTPS succeeds (HTTP-level success executed over TLS)
     */
    rv = curl_http_post(https_url, US748_PKCS10_CT, US748_PKCS10_RSA2048,
                        US748_UIDPWD_GOOD, US748_CACERTS, CURLAUTH_BASIC, NULL, NULL, NULL);
    CU_ASSERT(rv == 200);

    /*
     * Construct a plain HTTP URL from the HTTPS enroll URL and verify the
     * server rejects or fails the enrollment (i.e., HTTP messages must be
     * transported over TLS).
     */
    if (strncmp(https_url, "https://", 8) == 0) {
        snprintf(http_url, sizeof(http_url), "http://%s", https_url + 8);
    } else {
        /* Fallback: prepend http:// if the URL does not begin with https:// */
        snprintf(http_url, sizeof(http_url), "http://%s", https_url);
    }

    rv = curl_http_post(http_url, US748_PKCS10_CT, US748_PKCS10_RSA2048,
                        US748_UIDPWD_GOOD, US748_CACERTS, CURLAUTH_BASIC, NULL, NULL, NULL);
    /* Expect a non-200 result when attempting to use plain HTTP for an endpoint
     * that requires TLS transport. */
    CU_ASSERT(rv != 200);
}
