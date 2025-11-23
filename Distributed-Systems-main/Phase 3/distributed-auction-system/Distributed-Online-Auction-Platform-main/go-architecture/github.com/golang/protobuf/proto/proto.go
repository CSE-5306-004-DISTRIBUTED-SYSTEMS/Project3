package proto

import "fmt"

type Message interface{}

const ProtoPackageIsVersion4 = 4

func CompactTextString(m Message) string {
    return fmt.Sprintf("%+v", m)
}

