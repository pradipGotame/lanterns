/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ17_chunk0_missing_test_1.c
 */

#include <string.h>

static void rq17_chunk0_missing_test_1 (void)
{
    long rv;

    LOG_FUNC_NM
    ;

    SLEEP(1);

    /*
     * Happy-path acceptance of a valid single path segment: expect 200
     */
    rv = curl_http_post(US894_ENROLL_URL,
                        US894_PKCS10_CT,
                        US894_PKCS10_REQ,
                        US894_UIDPWD_GOOD,
                        US894_CACERTS,
                        CURLAUTH_BASIC,
                        NULL,
                        NULL,
                        NULL);
    /*
     * Since we passed in valid credentials and a standard enroll URL,
     * we expect the server to respond with 200
     */
    CU_ASSERT(rv == 200);

    /*
     * Operation-identical segment ambiguity: ensure the server and proxy
     * observed the path-segment string and assert the documented error
     * behaviour (original test comment expects a 400).
     */
    memset(tst_srvr_path_seg_enroll, 0, EST_MAX_PATH_SEGMENT_LEN + 1);
    memset(tst_proxy_path_seg_auth, 0, EST_MAX_PATH_SEGMENT_LEN + 1);

    rv = curl_http_post(US3512_PROXY_ENROLL_URL_CONTAINS_OPERATION,
                        US3512_PKCS10_CT, US3512_PKCS10_REQ,
                        US3512_UIDPWD_GOOD, US3512_CACERTS, CURLAUTH_BASIC, NULL, NULL, NULL);

    CU_ASSERT(strcmp(PATH_SEG_CONTAINS_OPERATION, tst_srvr_path_seg_enroll) == 0);
    CU_ASSERT(strcmp(PATH_SEG_CONTAINS_OPERATION, tst_proxy_path_seg_auth) == 0);

    /*
     * The original test comment indicates a 400 is expected when a path
     * segment equals an operation. Assert that behavior to close the gap.
     */
    CU_ASSERT(rv == 400);
}
